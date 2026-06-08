"use strict";

const CUSTOM = "custom";

const el = (id) => document.getElementById(id);
const ui = {
  format: el("format"),
  customPick: el("customPick"),
  customMax: el("customMax"),
  count: el("count"),
  unique: el("unique"),
  generate: el("generate"),
  clear: el("clear"),
  copyAll: el("copyAll"),
  saveTxt: el("saveTxt"),
  exportCsv: el("exportCsv"),
  results: el("results"),
  empty: el("empty"),
  status: el("status"),
  themeToggle: el("themeToggle"),
};

let presets = [];
let maxSets = 1000;
let lastSets = []; // array of number arrays
let lastPad = 2;

// --------------------------------------------------------------------------- //
// Theme
// --------------------------------------------------------------------------- //
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  ui.themeToggle.textContent = theme === "dark" ? "☀ Light" : "🌙 Dark";
  localStorage.setItem("theme", theme);
}
ui.themeToggle.addEventListener("click", () => {
  const next =
    document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
  applyTheme(next);
});

// --------------------------------------------------------------------------- //
// Status helpers
// --------------------------------------------------------------------------- //
function setStatus(message, isError = false) {
  ui.status.textContent = message;
  ui.status.classList.toggle("error", isError);
}

// --------------------------------------------------------------------------- //
// Load presets
// --------------------------------------------------------------------------- //
async function loadPresets() {
  try {
    const res = await fetch("api/presets");
    const data = await res.json();
    presets = data.presets || [];
    maxSets = data.max_sets || 1000;
  } catch {
    presets = [
      { name: "6/49", pick: 6, max_number: 49 },
      { name: "6/58", pick: 6, max_number: 58 },
    ];
  }
  ui.count.max = String(maxSets);
  for (const p of presets) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.name;
    opt.dataset.pick = p.pick;
    opt.dataset.max = p.max_number;
    ui.format.appendChild(opt);
  }
  const custom = document.createElement("option");
  custom.value = CUSTOM;
  custom.textContent = "Custom…";
  ui.format.appendChild(custom);
  syncCustomVisibility();
}

function syncCustomVisibility() {
  const isCustom = ui.format.value === CUSTOM;
  document.querySelectorAll(".custom-only").forEach((node) => {
    node.classList.toggle("hidden", !isCustom);
  });
}
ui.format.addEventListener("change", syncCustomVisibility);

// --------------------------------------------------------------------------- //
// Resolve selected format -> {pick, max_number}
// --------------------------------------------------------------------------- //
function resolveFormat() {
  if (ui.format.value === CUSTOM) {
    return {
      pick: parseInt(ui.customPick.value, 10),
      max_number: parseInt(ui.customMax.value, 10),
    };
  }
  const opt = ui.format.selectedOptions[0];
  return {
    pick: parseInt(opt.dataset.pick, 10),
    max_number: parseInt(opt.dataset.max, 10),
  };
}

// --------------------------------------------------------------------------- //
// Rendering
// --------------------------------------------------------------------------- //
function render(sets) {
  ui.results.innerHTML = "";
  ui.empty.classList.toggle("hidden", sets.length > 0);

  sets.forEach((entry, idx) => {
    const card = document.createElement("div");
    card.className = "set-card";

    const head = document.createElement("div");
    head.className = "set-head";
    const label = document.createElement("span");
    label.textContent = `Set ${idx + 1}`;
    const copyBtn = document.createElement("button");
    copyBtn.className = "set-copy";
    copyBtn.textContent = "Copy";
    copyBtn.addEventListener("click", () => {
      copyText(entry.formatted);
      setStatus(`Copied set ${idx + 1}.`);
    });
    head.append(label, copyBtn);

    const balls = document.createElement("div");
    balls.className = "balls";
    entry.numbers.forEach((n) => {
      const ball = document.createElement("div");
      ball.className = "ball";
      ball.textContent = String(n).padStart(lastPad, "0");
      balls.appendChild(ball);
    });

    card.append(head, balls);
    ui.results.appendChild(card);
  });
}

// --------------------------------------------------------------------------- //
// Generate
// --------------------------------------------------------------------------- //
async function generate() {
  const fmt = resolveFormat();
  const count = parseInt(ui.count.value, 10);

  if (!Number.isInteger(count) || count < 1 || count > maxSets) {
    setStatus(`Sets must be between 1 and ${maxSets}.`, true);
    return;
  }
  if (!Number.isInteger(fmt.pick) || !Number.isInteger(fmt.max_number)) {
    setStatus("Custom format needs valid whole numbers.", true);
    return;
  }
  if (fmt.max_number < fmt.pick) {
    setStatus("Highest number must be at least the numbers-per-set.", true);
    return;
  }

  ui.generate.disabled = true;
  setStatus("Generating…");
  try {
    const res = await fetch("api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...fmt, count, unique: ui.unique.checked }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.error || "Generation failed.", true);
      return;
    }
    lastSets = data.sets.map((s) => s.numbers);
    lastPad = data.pad_width;
    render(data.sets);
    setStatus(`Generated ${data.count} set(s) for ${data.format}.`);
  } catch (err) {
    setStatus("Network error: " + err.message, true);
  } finally {
    ui.generate.disabled = false;
  }
}

// --------------------------------------------------------------------------- //
// Clear / copy / export
// --------------------------------------------------------------------------- //
function clearResults() {
  lastSets = [];
  render([]);
  setStatus("Cleared.");
}

function formattedAll() {
  return lastSets
    .map((nums, i) => {
      const body = nums.map((n) => String(n).padStart(lastPad, "0")).join(" - ");
      return `${String(i + 1).padStart(String(lastSets.length).length, " ")}.  ${body}`;
    })
    .join("\n");
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
}

function copyAll() {
  if (!lastSets.length) return setStatus("Nothing to copy.", true);
  copyText(formattedAll());
  setStatus(`Copied all ${lastSets.length} set(s).`);
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function saveTxt() {
  if (!lastSets.length) return setStatus("Nothing to save.", true);
  download("lottery.txt", formattedAll() + "\n", "text/plain");
  setStatus("Saved TXT.");
}

function exportCsv() {
  if (!lastSets.length) return setStatus("Nothing to export.", true);
  const pick = lastSets[0].length;
  const header = ["Set", ...Array.from({ length: pick }, (_, i) => `N${i + 1}`)];
  const rows = lastSets.map((nums, i) => [i + 1, ...nums].join(","));
  download("lottery.csv", [header.join(","), ...rows].join("\n") + "\n", "text/csv");
  setStatus("Exported CSV.");
}

// --------------------------------------------------------------------------- //
// Wire up
// --------------------------------------------------------------------------- //
ui.generate.addEventListener("click", generate);
ui.clear.addEventListener("click", clearResults);
ui.copyAll.addEventListener("click", copyAll);
ui.saveTxt.addEventListener("click", saveTxt);
ui.exportCsv.addEventListener("click", exportCsv);

applyTheme(localStorage.getItem("theme") || "light");
loadPresets();
