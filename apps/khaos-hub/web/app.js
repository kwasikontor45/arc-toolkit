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

// Mirror the local Arc/Kataleya circadian engine: interpolate the same four
// ambient anchors by local clock time, and keep functional phase accents.
const circadianAnchors = [
  {hour: 6, bg: "#201f30", surface: "#26243c", overlay: "#352f4d", fg: "#e3e0f2", muted: "#b4adc6"},
  {hour: 13, bg: "#0f1c24", surface: "#15252f", overlay: "#1e3542", fg: "#dbe8ec", muted: "#9fbec7"},
  {hour: 18, bg: "#2b2035", surface: "#342942", overlay: "#493655", fg: "#f1e7da", muted: "#b9a28e"},
  {hour: 24, bg: "#232136", surface: "#2a273f", overlay: "#393552", fg: "#e0def4", muted: "#aaa7c0"}
];
const phaseAccents = {choice: "#5ec8ed", desire: "#f6c177", "still-pine": "#c4a7e7", nyx: "#ea9a97"};
function hexRgb(hex) { return hex.match(/[a-f\d]{2}/gi).map(value => parseInt(value, 16)); }
function rgbHex(rgb) { return `#${rgb.map(value => Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, "0")).join("")}`; }
function blendHex(a, b, amount) {
  const aa = hexRgb(a), bb = hexRgb(b);
  return rgbHex(aa.map((value, index) => value + (bb[index] - value) * amount));
}
function circadianPhase(hour) {
  if (hour < 6 || hour >= 21) return "nyx";
  if (hour < 11) return "choice";
  if (hour < 17) return "desire";
  return "still-pine";
}
function updateCircadianTheme() {
  const now = new Date();
  let hour = now.getHours() + now.getMinutes() / 60;
  const effectiveHour = hour < 6 ? hour + 24 : hour;
  let first = circadianAnchors[3], second = circadianAnchors[0], position = (effectiveHour - 24) / 6;
  for (let index = 0; index < circadianAnchors.length; index += 1) {
    const a = circadianAnchors[index];
    const b = circadianAnchors[(index + 1) % circadianAnchors.length];
    const end = b.hour > a.hour ? b.hour : b.hour + 24;
    if (effectiveHour >= a.hour && effectiveHour < end) {
      first = a; second = b; position = (effectiveHour - a.hour) / (end - a.hour); break;
    }
  }
  const root = document.documentElement;
  const colors = {};
  for (const role of ["bg", "surface", "overlay", "fg", "muted"]) colors[role] = blendHex(first[role], second[role], position);
  const accent = phaseAccents[circadianPhase(hour)];
  const rgb = color => hexRgb(color).join(",");
  root.style.setProperty("--ink", colors.bg);
  root.style.setProperty("--ink-rgb", rgb(colors.bg));
  root.style.setProperty("--surface-rgb", rgb(colors.surface));
  root.style.setProperty("--overlay-rgb", rgb(colors.overlay));
  root.style.setProperty("--paper", colors.fg);
  root.style.setProperty("--paper-rgb", rgb(colors.fg));
  root.style.setProperty("--muted", colors.muted);
  root.style.setProperty("--phase-rgb", rgb(accent));
  root.style.setProperty("--mint", accent);
}
updateCircadianTheme();
setInterval(updateCircadianTheme, 60_000);

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
    const kind = String(item.kind || "to-do");
    const rowType = kind.toLowerCase().includes("event") ? "event" : "todo";
    const label = document.createElement("label");
    label.className = `calendar-row calendar-${rowType}${item.done ? " is-complete" : ""}`;
    const input = document.createElement("input"); input.type = "checkbox";
    input.checked = item.done; input.dataset.calendarId = item.id;
    input.setAttribute("aria-label", `Mark ${item.title} complete`);
    const text = document.createElement("span"); text.className = "calendar-copy";
    const title = document.createElement("strong"); title.textContent = item.title;
    const meta = document.createElement("span"); meta.className = "calendar-meta";
    const kindBadge = document.createElement("small"); kindBadge.className = "calendar-kind"; kindBadge.textContent = kind;
    const when = document.createElement("small"); when.className = "calendar-when"; when.textContent = item.when;
    meta.append(kindBadge, when); text.append(title, meta); label.append(input, text);
    input.addEventListener("change", async () => {
      if (calendarBusy) { input.checked = item.done; return; }
      label.classList.toggle("is-complete", input.checked);
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
