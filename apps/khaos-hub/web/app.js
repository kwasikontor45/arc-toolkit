"use strict";

const cards = [
  { title: "Host & Tailnet", source: "Host availability and Tailscale status", values: ["Online", "Online", "Offline"], tones: ["mint", "mint", "coral"] },
  { title: "Host health", source: "Reduced arc health summary", values: ["Nominal", "1 warning", "Unavailable"], tones: ["mint", "amber", "coral"] },
  { title: "Services", source: "System and user failed-unit counts", values: ["1 needs review", "2 failed", "Unavailable"], tones: ["amber", "coral", "coral"] },
  { title: "SOC / IDS", source: "Suricata and read-only container state", values: ["Monitoring", "Not sampled", "Unavailable"], tones: ["blue", "amber", "coral"] },
  { title: "Backup", source: "Last successful vault completion marker", values: ["6h ago", "Stale · 26h", "Cached · stale"], tones: ["mint", "coral", "amber"] },
  { title: "Inventory", source: "Generated inventory aggregate only", values: ["134 assets", "134 tracked", "Last snapshot"], tones: ["mint", "amber", "amber"] },
  { title: "Cloud lab", source: "Minimal read-only cloud state and budget", values: ["Paused", "Partial", "Unavailable"], tones: ["blue", "amber", "coral"] }
];

let scenario = 0;
let activePage = "overview";

function renderCards() {
  const grid = document.querySelector("#status-grid");
  const fragment = document.createDocumentFragment();
  cards.forEach((card) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "status-card";
    button.classList.add(`tone-${card.tones[scenario]}`);
    button.setAttribute("aria-label", `${card.title}, sample status ${card.values[scenario]}. Show planned source.`);

    const head = document.createElement("span");
    head.className = "card-head";
    const name = document.createElement("span");
    name.className = "card-name";
    name.textContent = card.title;
    const dot = document.createElement("span");
    dot.className = "card-dot";
    dot.setAttribute("aria-hidden", "true");
    head.append(name, dot);

    const value = document.createElement("span");
    value.className = "card-value";
    value.textContent = card.values[scenario];
    const foot = document.createElement("span");
    foot.className = "card-foot";
    foot.textContent = "SAMPLE STATE";
    button.append(head, value, foot);
    button.addEventListener("click", () => showDetail(card));
    fragment.append(button);
  });
  grid.replaceChildren(fragment);
}

function showDetail(card) {
  const dialog = document.querySelector(".detail-dialog");
  document.querySelector("#detail-title").textContent = card.title;
  document.querySelector("#detail-value").textContent = `Preview value: ${card.values[scenario]}`;
  document.querySelector("#detail-source").textContent = `Planned source: ${card.source}.`;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else window.alert(`${card.title}\n${card.values[scenario]}\n${card.source}\nFixture only.`);
}

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", () => {
    scenario = Number(button.dataset.scenario);
    document.querySelectorAll("[data-scenario]").forEach((option) => {
      const selected = option === button;
      option.classList.toggle("is-selected", selected);
      option.setAttribute("aria-pressed", String(selected));
    });
    renderCards();
    document.querySelector(".preview-banner").setAttribute("aria-label", `Local fixture preview, ${button.textContent} scenario. No host connection.`);
  });
});

document.querySelectorAll("[data-page]").forEach((button) => {
  button.addEventListener("click", () => {
    activePage = button.dataset.page;
    document.querySelectorAll("[data-view]").forEach((page) => {
      page.hidden = page.dataset.view !== activePage;
    });
    document.querySelectorAll("[data-page]").forEach((navigationButton) => {
      const selected = navigationButton.dataset.page === activePage;
      navigationButton.classList.toggle("is-active", selected);
      if (selected) navigationButton.setAttribute("aria-current", "page");
      else navigationButton.removeAttribute("aria-current");
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
});

document.querySelector(".detail-dialog").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) event.currentTarget.close();
});

renderCards();

let calendarToken = "";
let calendarBusy = false;
let calendarSignature = "";
async function calendarRequest(path, options = {}) {
  const response = await fetch(path, {cache: "no-store", ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Calendar unavailable");
  return data;
}
function showCalendar(data) {
  const signature = JSON.stringify(data.items);
  document.querySelector("#calendar-state").textContent = "Live · updates every 2 seconds";
  if (signature === calendarSignature) return;
  calendarSignature = signature;
  const list = document.querySelector("#calendar-list");
  const activeId = document.activeElement?.dataset?.calendarId;
  const fragment = document.createDocumentFragment();
  data.items.forEach(item => {
    const label = document.createElement("label"); label.className = "calendar-row";
    const input = document.createElement("input"); input.type = "checkbox";
    input.checked = item.done; input.dataset.calendarId = item.id;
    input.setAttribute("aria-label", `Mark ${item.title} complete`);
    const text = document.createElement("span");
    const title = document.createElement("strong"); title.textContent = item.title;
    const when = document.createElement("small"); when.textContent = `${item.kind} · ${item.when}`;
    text.append(title, when); label.append(input, text);
    input.addEventListener("change", async () => {
      if (calendarBusy) { input.checked = item.done; return; }
      calendarBusy = true; input.disabled = true;
      try {
        if (!calendarToken) calendarToken = (await calendarRequest("/api/session")).token;
        const saved = await calendarRequest("/api/calendar/check", {method: "POST", headers: {"Content-Type": "application/json", "X-Hub-Token": calendarToken}, body: JSON.stringify({id: item.id, done: input.checked, revision: item.revision})});
        showCalendar(saved);
      } catch (error) {
        input.checked = item.done; calendarToken = "";
        document.querySelector("#calendar-state").textContent = `${error.message}. Your change was not saved.`;
        calendarSignature = "";
      } finally { calendarBusy = false; input.disabled = false; }
    });
    fragment.append(label);
  });
  if (!data.items.length) fragment.append(document.createTextNode("No events in the next two weeks or to-dos."));
  list.replaceChildren(fragment);
  if (activeId) Array.from(list.querySelectorAll("input")).find(input => input.dataset.calendarId === activeId)?.focus();
}
async function refreshCalendar() {
  if (calendarBusy || document.hidden) return;
  calendarBusy = true;
  try { showCalendar(await calendarRequest("/api/calendar")); }
  catch (error) {
    document.querySelector("#calendar-state").textContent = `${error.message}. Check marks are unavailable.`;
    document.querySelectorAll("#calendar-list input").forEach(input => input.disabled = true);
    calendarSignature = "";
  } finally { calendarBusy = false; }
}
setInterval(refreshCalendar, 2000);
document.addEventListener("visibilitychange", refreshCalendar);
refreshCalendar();
