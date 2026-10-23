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
  {hour: 6, bg: "#131a19", surface: "#1a2421", overlay: "#26332e", fg: "#e3eae6", muted: "#a6b3ac"},
  {hour: 13, bg: "#0c1717", surface: "#142322", overlay: "#1d302e", fg: "#dcece8", muted: "#93aaa5"},
  {hour: 18, bg: "#1a1712", surface: "#242018", overlay: "#342d20", fg: "#efe7d7", muted: "#b3a183"},
  {hour: 24, bg: "#0c1211", surface: "#121d1a", overlay: "#192723", fg: "#e5eee8", muted: "#9caaa2"}
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
  const phase = circadianPhase(hour);
  const phaseChip = document.querySelector(".phase-chip");
  if (phaseChip) phaseChip.textContent = phase.toUpperCase();
  const state = document.querySelector(".topbar-state");
  if (state) state.setAttribute("aria-label", "Khaos-Lab 418 Dev-Studio · " + phase + " phase");
  const accent = phaseAccents[phase];
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
let showCompleted = false;
const expandedCalendarGroups = new Set(["To-dos"]);
const expandedCalendarRows = new Set();
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
  const active = data.items.filter(item => !item.done);
  const complete = data.items.filter(item => item.done);
  const groups = [
    ["To-dos", "todo", active.filter(item => item.kind === "To-do")],
    ["Appointments", "appointment", active.filter(item => item.kind === "Appointment")],
    ["Events", "event", active.filter(item => item.kind === "Event")]
  ];
  function makeRow(item, rowType) {
    const kind = String(item.kind || "to-do");
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
    return label;
  }
  groups.forEach(([name, type, items]) => {
    const section = document.createElement("section"); section.className = "calendar-group";
    const heading = document.createElement("button"); heading.type = "button";
    heading.className = "calendar-group-toggle";
    const open = expandedCalendarGroups.has(name);
    heading.setAttribute("aria-expanded", String(open));
    heading.textContent = `${open ? "−" : "+"}  ${name} · ${items.length}`;
    heading.addEventListener("click", () => {
      if (open) expandedCalendarGroups.delete(name); else expandedCalendarGroups.add(name);
      calendarSignature = ""; showCalendar(data);
    });
    section.append(heading);
    if (open) {
      if (!items.length) {
        const empty = document.createElement("p"); empty.className = "calendar-empty";
        empty.textContent = "Nothing scheduled in this two-week window."; section.append(empty);
      }
      const visible = expandedCalendarRows.has(name) ? items : items.slice(0, 10);
      visible.forEach(item => section.append(makeRow(item, type)));
      if (items.length > 10) {
        const more = document.createElement("button"); more.type = "button";
        more.className = "calendar-more-toggle";
        more.textContent = expandedCalendarRows.has(name) ? "Show fewer" : `Show all · ${items.length - 10} more`;
        more.addEventListener("click", () => {
          if (expandedCalendarRows.has(name)) expandedCalendarRows.delete(name); else expandedCalendarRows.add(name);
          calendarSignature = ""; showCalendar(data);
        });
        section.append(more);
      }
    }
    fragment.append(section);
  });
  if (complete.length) {
    const toggle = document.createElement("button"); toggle.type = "button";
    toggle.className = "calendar-completed-toggle";
    toggle.setAttribute("aria-expanded", String(showCompleted));
    toggle.textContent = `${showCompleted ? "Hide" : "Show"} completed · ${complete.length}`;
    toggle.addEventListener("click", () => { showCompleted = !showCompleted; calendarSignature = ""; showCalendar(data); });
    fragment.append(toggle);
    if (showCompleted) {
      const visible = expandedCalendarRows.has("Completed") ? complete : complete.slice(0, 10);
      visible.forEach(item => fragment.append(makeRow(item, "completed")));
      if (complete.length > 10) {
        const more = document.createElement("button"); more.type = "button";
        more.className = "calendar-more-toggle";
        more.textContent = expandedCalendarRows.has("Completed") ? "Show fewer completed" : `Show all completed · ${complete.length - 10} more`;
        more.addEventListener("click", () => {
          if (expandedCalendarRows.has("Completed")) expandedCalendarRows.delete("Completed"); else expandedCalendarRows.add("Completed");
          calendarSignature = ""; showCalendar(data);
        });
        fragment.append(more);
      }
    }
  }
  if (!data.items.length) fragment.append(document.createTextNode("Nothing scheduled in the next two weeks."));
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

// Private Library: saved references only; the import reads bookmark stores, never history or pages.
let libraryToken = "";
let libraryItems = [];
let browserScan = null;
let libraryVisibleLimit = 36;
const libraryKinds = {
  bookmark: "Bookmark", reading: "Reading list", tutorial: "Tutorial",
  research: "Research", incident: "Incident reference"
};
async function libraryRequest(path, options = {}) {
  const response = await fetch(path, { cache: "no-store", ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Library unavailable");
  return data;
}
async function libraryPost(path, payload) {
  if (!libraryToken) libraryToken = (await libraryRequest("/api/session")).token;
  return libraryRequest(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Hub-Token": libraryToken },
    body: JSON.stringify(payload)
  });
}
function updateLibraryStats() {
  const stats = document.querySelector("#library-stats");
  const labels = [["total", "Saved"], ["bookmark", "Bookmarks"], ["reading", "Reading"],
    ["tutorial", "Tutorials"], ["research", "Research"], ["incident", "Incidents"]];
  const fragment = document.createDocumentFragment();
  labels.forEach(([key, label]) => {
    const pill = document.createElement("span");
    pill.className = "library-stat";
    const count = document.createElement("strong");
    count.textContent = String(libraryItems.filter(item => key === "total" || item.kind === key).length);
    pill.append(count, document.createTextNode(label));
    fragment.append(pill);
  });
  stats.replaceChildren(fragment);
}
function renderLibrary() {
  const list = document.querySelector("#library-list");
  const query = document.querySelector("#library-search").value.trim().toLowerCase();
  const filter = document.querySelector("#library-filter").value;
  const fragment = document.createDocumentFragment();
  updateLibraryStats();
  const rows = libraryItems.filter(item => {
    const sourceText = (item.sources || []).map(source =>
      [source.browser, source.profile, source.folder, source.title].join(" ")).join(" ");
    return (filter === "all" || item.kind === filter) &&
      [item.title, item.url, item.tags, item.note, sourceText].join(" ").toLowerCase().includes(query);
  });
  rows.slice(0, libraryVisibleLimit).forEach(item => {
    const card = document.createElement("article");
    card.className = "library-card";
    const type = document.createElement("p");
    type.className = "eyebrow";
    type.textContent = libraryKinds[item.kind] || item.kind.toUpperCase();
    const title = document.createElement(item.url ? "a" : "h2");
    if (item.url) { title.href = item.url; title.target = "_blank"; title.rel = "noopener noreferrer"; }
    title.className = "library-card-title";
    title.textContent = item.title;
    const note = document.createElement("p");
    note.textContent = item.note || "No notes yet.";
    const meta = document.createElement("p");
    meta.className = "library-card-meta";
    meta.textContent = [item.tags, item.updated].filter(Boolean).join(" · ");
    const actions = document.createElement("div");
    actions.className = "library-card-actions";
    const edit = document.createElement("button");
    edit.type = "button";
    edit.textContent = "Edit";
    edit.addEventListener("click", () => {
      document.querySelector("#library-id").value = item.id;
      document.querySelector("#library-title-input").value = item.title;
      document.querySelector("#library-url-input").value = item.url;
      document.querySelector("#library-kind").value = item.kind;
      document.querySelector("#library-tags").value = item.tags;
      document.querySelector("#library-note").value = item.note;
      document.querySelector("#library-cancel").hidden = false;
      document.querySelector("#library-title-input").focus();
    });
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      if (!confirm("Delete this local reference?")) return;
      try {
        const data = await libraryPost("/api/library/delete", { id: item.id });
        libraryItems = data.items;
        libraryVisibleLimit = 36;
        renderLibrary();
        document.querySelector("#library-state").textContent = "Reference removed from this computer.";
      } catch (error) { document.querySelector("#library-state").textContent = error.message; }
    });
    actions.append(edit, del);
    card.append(type, title, note, meta, actions);
    if (item.sources?.length) {
      const details = document.createElement("details");
      details.className = "library-source";
      const summary = document.createElement("summary");
      summary.textContent = `Saved from ${item.sources.length} source${item.sources.length === 1 ? "" : "s"}`;
      const sourceList = document.createElement("ul");
      item.sources.forEach(source => {
        const row = document.createElement("li");
        row.textContent = [source.browser, source.profile, source.folder].filter(Boolean).join(" · ");
        sourceList.append(row);
      });
      details.append(summary, sourceList);
      card.append(details);
    }
    fragment.append(card);
  });
  list.replaceChildren(fragment);
  if (rows.length > libraryVisibleLimit) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "library-load-more";
    more.textContent = `Show next 36 · ${rows.length - libraryVisibleLimit} remaining`;
    more.addEventListener("click", () => { libraryVisibleLimit += 36; renderLibrary(); });
    list.append(more);
  }
  if (!rows.length) {
    const empty = document.createElement("p");
    empty.className = "library-empty";
    empty.textContent = query ? "No matching references." : "Your library is empty. Add a reference above.";
    list.append(empty);
  }
}
async function loadLibrary() {
  try {
    libraryItems = (await libraryRequest("/api/library")).items;
    libraryVisibleLimit = 36;
    renderLibrary();
    document.querySelector("#library-state").textContent = `${libraryItems.length} saved locally on this computer.`;
  } catch (error) { document.querySelector("#library-state").textContent = error.message; }
}
async function saveLibrary(path, payload) {
  const data = await libraryPost(path, payload);
  libraryItems = data.items;
  libraryVisibleLimit = 36;
  renderLibrary();
  document.querySelector("#library-state").textContent = `${libraryItems.length} saved locally on this computer.`;
}
document.querySelector("#library-form").addEventListener("submit", async event => {
  event.preventDefault();
  const payload = {
    id: document.querySelector("#library-id").value || undefined,
    title: document.querySelector("#library-title-input").value,
    url: document.querySelector("#library-url-input").value,
    kind: document.querySelector("#library-kind").value,
    tags: document.querySelector("#library-tags").value,
    note: document.querySelector("#library-note").value
  };
  try {
    await saveLibrary("/api/library/save", payload);
    event.currentTarget.reset();
    document.querySelector("#library-id").value = "";
    document.querySelector("#library-cancel").hidden = true;
  } catch (error) { document.querySelector("#library-state").textContent = error.message; }
});
document.querySelector("#library-cancel").addEventListener("click", () => {
  document.querySelector("#library-form").reset();
  document.querySelector("#library-id").value = "";
  document.querySelector("#library-cancel").hidden = true;
});
document.querySelector("#library-search").addEventListener("input", () => { libraryVisibleLimit = 36; renderLibrary(); });
document.querySelector("#library-filter").addEventListener("change", () => { libraryVisibleLimit = 36; renderLibrary(); });
document.querySelector("#library-export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify({ version: 1, items: libraryItems }, null, 2)], { type: "application/json" });
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = "khaos-hub-library.json";
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(anchor.href), 1000);
});
document.querySelector("#library-import-file").addEventListener("change", async event => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    if (file.size > 8 * 1024 * 1024) throw new Error("File is over the 8 MiB import limit.");
    const imported = JSON.parse(await file.text());
    if (imported.version !== 1 || !Array.isArray(imported.items) || imported.items.length > 10000)
      throw new Error("Unsupported file or item count.");
    if (!confirm(`Import ${imported.items.length} references into this computer's local library?`)) return;
    const result = await libraryPost("/api/library/import", { items: imported.items });
    libraryItems = result.items;
    libraryVisibleLimit = 36;
    renderLibrary();
    document.querySelector("#library-state").textContent =
      `Imported: ${result.added} new · ${result.merged} matched and merged · ${result.duplicates_in_batch} duplicates consolidated.`;
  } catch (error) { document.querySelector("#library-state").textContent = `Import stopped: ${error.message}`; }
  finally { event.target.value = ""; }
});
function showBrowserPreview(preview) {
  const box = document.querySelector("#library-import-preview");
  const fragment = document.createDocumentFragment();
  const summary = document.createElement("p");
  summary.textContent = `${preview.total} saved bookmark entries found in ${preview.counts.length} profiles. Estimate: add ${preview.will_add}, merge ${preview.matching} existing links, consolidate ${preview.duplicates_in_scan} repeats. Titles, links, and folder names stay on this computer; browsing history and page contents are not read.`;
  fragment.append(summary);
  preview.counts.forEach(source => {
    const row = document.createElement("p");
    row.textContent = `${source.browser} · ${source.profile}: ${source.count} saved · ${source.reading} marked as reading`;
    fragment.append(row);
  });
  if (preview.errors.length) {
    const warning = document.createElement("p");
    warning.textContent = `Could not read every profile: ${preview.errors.join("; ")}. Fix or close the affected browser profile, then scan again.`;
    fragment.append(warning);
  }
  const proceed = document.createElement("button");
  proceed.type = "button";
  proceed.textContent = "Import and merge duplicates";
  proceed.disabled = preview.errors.length > 0 || preview.total === 0;
  proceed.addEventListener("click", async () => {
    if (!browserScan || !confirm(`Import ${preview.total} saved browser bookmarks into the local Library? Duplicates will merge and originals will remain unchanged.`)) return;
    proceed.disabled = true;
    document.querySelector("#library-state").textContent = "Importing local bookmarks…";
    try {
      const result = await libraryPost("/api/library/browser-import", { scan_id: browserScan, confirmed: true });
      libraryItems = result.items;
      libraryVisibleLimit = 36;
      renderLibrary();
      document.querySelector("#library-state").textContent =
        `Added ${result.added} · merged ${result.merged} existing links · consolidated ${result.duplicates_in_batch} repeats. Local backup created: ${result.backup_created ? "yes" : "not needed"}.`;
      box.hidden = true;
      browserScan = null;
    } catch (error) {
      document.querySelector("#library-state").textContent = error.message;
      proceed.disabled = false;
    }
  });
  if (!preview.errors.length) fragment.append(proceed);
  box.replaceChildren(fragment);
  box.hidden = false;
}
document.querySelector("#library-browser-scan").addEventListener("click", async event => {
  const button = event.currentTarget;
  button.disabled = true;
  browserScan = null;
  document.querySelector("#library-state").textContent = "Scanning saved browser bookmarks on this computer…";
  try {
    const preview = await libraryRequest("/api/library/browser-preview");
    browserScan = preview.scan_id;
    showBrowserPreview(preview);
    document.querySelector("#library-state").textContent = preview.message;
  } catch (error) { document.querySelector("#library-state").textContent = error.message; }
  finally { button.disabled = false; }
});
loadLibrary();
