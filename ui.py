"""Tkinter desktop UI for the lottery number generator.

A clean, modern, object-oriented interface with:
  * format selection (6/49, 6/58 or a custom format),
  * a count input with validation (1..1000 sets),
  * a "unique across session" toggle,
  * a scrollable results area,
  * Generate / Clear / Save TXT / Export CSV / Copy buttons,
  * a dark-mode toggle.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List

from generator import (
    DEFAULT_FORMAT,
    MAX_SETS,
    PRESETS,
    CombinationGenerator,
    GenerationError,
    LotteryFormat,
)
from utils import (
    combos_to_csv,
    combos_to_txt,
    format_results,
    validate_count,
    validate_custom_format,
)

CUSTOM_LABEL = "Custom…"
APP_TITLE = "Lottery Number Generator"


# --------------------------------------------------------------------------- #
# Theming
# --------------------------------------------------------------------------- #
class Theme:
    """A flat colour palette for one appearance mode."""

    def __init__(self, **colors: str) -> None:
        self.bg = colors["bg"]
        self.surface = colors["surface"]
        self.text = colors["text"]
        self.muted = colors["muted"]
        self.accent = colors["accent"]
        self.accent_active = colors["accent_active"]
        self.accent_text = colors["accent_text"]
        self.border = colors["border"]
        self.field_bg = colors["field_bg"]
        self.console_bg = colors["console_bg"]
        self.console_fg = colors["console_fg"]


LIGHT = Theme(
    bg="#f4f6fb",
    surface="#ffffff",
    text="#1e272e",
    muted="#6b7280",
    accent="#2e86de",
    accent_active="#1b6fc4",
    accent_text="#ffffff",
    border="#d7dce5",
    field_bg="#ffffff",
    console_bg="#ffffff",
    console_fg="#1e272e",
)

DARK = Theme(
    bg="#1e1f26",
    surface="#2a2c36",
    text="#e8eaed",
    muted="#9aa0ad",
    accent="#4c8dff",
    accent_active="#3a7bef",
    accent_text="#ffffff",
    border="#3a3d49",
    field_bg="#22232c",
    console_bg="#14151a",
    console_fg="#e8eaed",
)


class LotteryApp(ttk.Frame):
    """Root application frame."""

    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.master = master
        self.style = ttk.Style()
        self.dark_mode = False
        self.theme = LIGHT

        self.generator = CombinationGenerator(DEFAULT_FORMAT)
        self.current_combos: List[List[int]] = []
        self.current_format: LotteryFormat = DEFAULT_FORMAT

        # Tk variables ---------------------------------------------------
        self.format_var = tk.StringVar(value=DEFAULT_FORMAT.name)
        self.count_var = tk.StringVar(value="5")
        self.unique_var = tk.BooleanVar(value=False)
        self.custom_name_var = tk.StringVar(value="My Lottery")
        self.custom_pick_var = tk.StringVar(value="6")
        self.custom_max_var = tk.StringVar(value="49")
        self.status_var = tk.StringVar(value="Ready.")

        self._build_layout()
        self.apply_theme()
        self.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # results row stretches

        self._build_header()
        self._build_controls()
        self._build_results()
        self._build_statusbar()

    def _build_header(self) -> None:
        header = ttk.Frame(self, style="Header.TFrame", padding=(18, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="🎲  " + APP_TITLE, style="Title.TLabel")
        title.grid(row=0, column=0, sticky="w")

        self.theme_btn = ttk.Button(
            header, text="🌙  Dark mode", style="Ghost.TButton",
            command=self.toggle_theme,
        )
        self.theme_btn.grid(row=0, column=1, sticky="e")

    def _build_controls(self) -> None:
        panel = ttk.Frame(self, style="Surface.TFrame", padding=16)
        panel.grid(row=1, column=0, sticky="ew", padx=16, pady=(12, 6))
        for col in range(6):
            panel.columnconfigure(col, weight=0)

        # Format selection
        ttk.Label(panel, text="Format").grid(row=0, column=0, sticky="w", padx=(0, 8))
        formats = list(PRESETS.keys()) + [CUSTOM_LABEL]
        self.format_combo = ttk.Combobox(
            panel, textvariable=self.format_var, values=formats,
            state="readonly", width=12,
        )
        self.format_combo.grid(row=0, column=1, sticky="w", padx=(0, 18))
        self.format_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_format_change())

        # Count
        ttk.Label(panel, text="Sets").grid(row=0, column=2, sticky="w", padx=(0, 8))
        self.count_spin = ttk.Spinbox(
            panel, from_=1, to=MAX_SETS, textvariable=self.count_var, width=8,
        )
        self.count_spin.grid(row=0, column=3, sticky="w", padx=(0, 18))

        # Unique toggle
        self.unique_check = ttk.Checkbutton(
            panel, text="Unique sets (no repeats this session)",
            variable=self.unique_var, style="Switch.TCheckbutton",
        )
        self.unique_check.grid(row=0, column=4, sticky="w")

        # Custom-format row (hidden unless "Custom…" selected)
        self.custom_frame = ttk.Frame(panel, style="Surface.TFrame")
        self.custom_frame.grid(row=1, column=0, columnspan=6, sticky="w", pady=(12, 0))
        ttk.Label(self.custom_frame, text="Name").grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(self.custom_frame, textvariable=self.custom_name_var, width=16).grid(
            row=0, column=1, padx=(0, 16))
        ttk.Label(self.custom_frame, text="Numbers per set").grid(row=0, column=2, padx=(0, 6))
        ttk.Spinbox(self.custom_frame, from_=1, to=200, textvariable=self.custom_pick_var,
                    width=6).grid(row=0, column=3, padx=(0, 16))
        ttk.Label(self.custom_frame, text="Highest number").grid(row=0, column=4, padx=(0, 6))
        ttk.Spinbox(self.custom_frame, from_=1, to=999, textvariable=self.custom_max_var,
                    width=6).grid(row=0, column=5)
        self.custom_frame.grid_remove()  # hidden initially

        # Action buttons live on their own row, just above the results area.
        self.button_bar = ttk.Frame(self, style="TFrame", padding=(16, 4))
        self.button_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))

        self.generate_btn = ttk.Button(
            self.button_bar, text="✨  Generate", style="Accent.TButton",
            command=self.on_generate,
        )
        self.generate_btn.pack(side="left")

        ttk.Button(self.button_bar, text="Clear", command=self.on_clear).pack(
            side="left", padx=(8, 0))
        ttk.Button(self.button_bar, text="Save TXT", command=self.on_save_txt).pack(
            side="left", padx=(8, 0))
        ttk.Button(self.button_bar, text="Export CSV", command=self.on_export_csv).pack(
            side="left", padx=(8, 0))
        ttk.Button(self.button_bar, text="Copy all", command=self.on_copy_all).pack(
            side="left", padx=(8, 0))
        ttk.Button(self.button_bar, text="Copy selected",
                   command=self.on_copy_selected).pack(side="left", padx=(8, 0))

    def _build_results(self) -> None:
        wrap = ttk.Frame(self, style="Surface.TFrame", padding=2)
        wrap.grid(row=3, column=0, sticky="nsew", padx=16, pady=(6, 6))
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        self.output = ScrolledText(
            wrap, wrap="none", height=16, relief="flat", borderwidth=0,
            font=("Consolas", 13), padx=14, pady=12,
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        self.output.configure(state="disabled")

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self, style="Status.TFrame", padding=(16, 6))
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(bar, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Theming
    # ------------------------------------------------------------------ #
    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.theme = DARK if self.dark_mode else LIGHT
        self.theme_btn.configure(text="☀  Light mode" if self.dark_mode else "🌙  Dark mode")
        self.apply_theme()

    def apply_theme(self) -> None:
        t = self.theme
        self.style.theme_use("clam")
        self.master.configure(bg=t.bg)

        self.style.configure("TFrame", background=t.bg)
        self.style.configure("Surface.TFrame", background=t.surface,
                             bordercolor=t.border, relief="flat")
        self.style.configure("Header.TFrame", background=t.surface)
        self.style.configure("Status.TFrame", background=t.surface)

        self.style.configure("TLabel", background=t.surface, foreground=t.text)
        self.style.configure("Title.TLabel", background=t.surface, foreground=t.text,
                             font=("Segoe UI Semibold", 16))
        self.style.configure("Status.TLabel", background=t.surface, foreground=t.muted,
                             font=("Segoe UI", 9))

        # Buttons
        self.style.configure("TButton", background=t.surface, foreground=t.text,
                             bordercolor=t.border, focuscolor=t.surface, padding=(12, 7),
                             font=("Segoe UI", 10))
        self.style.map("TButton",
                       background=[("active", t.field_bg)],
                       foreground=[("disabled", t.muted)])

        self.style.configure("Accent.TButton", background=t.accent, foreground=t.accent_text,
                             bordercolor=t.accent, padding=(16, 8),
                             font=("Segoe UI Semibold", 10))
        self.style.map("Accent.TButton",
                       background=[("active", t.accent_active), ("pressed", t.accent_active)],
                       foreground=[("disabled", t.accent_text)])

        self.style.configure("Ghost.TButton", background=t.surface, foreground=t.text,
                             bordercolor=t.border, padding=(12, 6))
        self.style.map("Ghost.TButton", background=[("active", t.field_bg)])

        # Inputs
        for widget in ("TCombobox", "TSpinbox", "TEntry"):
            self.style.configure(widget, fieldbackground=t.field_bg, background=t.field_bg,
                                 foreground=t.text, bordercolor=t.border, arrowcolor=t.text,
                                 insertcolor=t.text, padding=4)
            self.style.map(widget, fieldbackground=[("readonly", t.field_bg)],
                           foreground=[("readonly", t.text)])

        self.style.configure("TCheckbutton", background=t.surface, foreground=t.text)
        self.style.configure("Switch.TCheckbutton", background=t.surface, foreground=t.text)
        self.style.map("TCheckbutton", background=[("active", t.surface)],
                       foreground=[("active", t.text)])

        # Output console
        self.output.configure(background=t.console_bg, foreground=t.console_fg,
                             insertbackground=t.console_fg,
                             selectbackground=t.accent, selectforeground=t.accent_text)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _on_format_change(self) -> None:
        if self.format_var.get() == CUSTOM_LABEL:
            self.custom_frame.grid()
        else:
            self.custom_frame.grid_remove()

    def _resolve_format(self) -> LotteryFormat:
        """Return the LotteryFormat currently selected in the UI."""
        choice = self.format_var.get()
        if choice == CUSTOM_LABEL:
            return validate_custom_format(
                self.custom_name_var.get(),
                self.custom_pick_var.get(),
                self.custom_max_var.get(),
            )
        return PRESETS[choice]

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _write_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    # ------------------------------------------------------------------ #
    # Button handlers
    # ------------------------------------------------------------------ #
    def on_generate(self) -> None:
        try:
            count = validate_count(self.count_var.get())
            fmt = self._resolve_format()
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        unique = self.unique_var.get()

        # Re-create the generator when the format changes so session-uniqueness
        # tracking is scoped to one format at a time.
        if fmt != self.current_format:
            self.generator = CombinationGenerator(fmt)
            self.current_format = fmt

        try:
            combos = self.generator.generate_many(count, unique=unique)
        except GenerationError as exc:
            messagebox.showerror("Cannot generate", str(exc))
            return

        self.current_combos = combos
        self._write_output(format_results(combos, pad_width=fmt.pad_width))
        seen = f" · {self.generator.seen_count} unique kept" if unique else ""
        self.set_status(f"Generated {count} set(s) for {fmt.name}.{seen}")

    def on_clear(self) -> None:
        self.current_combos = []
        self._write_output("")
        self.generator.reset_session()
        self.set_status("Cleared. Session uniqueness reset.")

    def on_save_txt(self) -> None:
        if not self._ensure_results():
            return
        path = filedialog.asksaveasfilename(
            title="Save results as TXT", defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"lottery_{self.current_format.name.replace('/', '-')}.txt",
        )
        if not path:
            return
        try:
            payload = combos_to_txt(self.current_combos, self.current_format.pad_width)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc))
            return
        self.set_status(f"Saved {len(self.current_combos)} set(s) to {path}")

    def on_export_csv(self) -> None:
        if not self._ensure_results():
            return
        path = filedialog.asksaveasfilename(
            title="Export results as CSV", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"lottery_{self.current_format.name.replace('/', '-')}.csv",
        )
        if not path:
            return
        try:
            payload = combos_to_csv(self.current_combos, self.current_format.pick)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(payload)
        except OSError as exc:
            messagebox.showerror("Export failed", str(exc))
            return
        self.set_status(f"Exported {len(self.current_combos)} set(s) to {path}")

    def on_copy_all(self) -> None:
        if not self._ensure_results():
            return
        text = format_results(self.current_combos, pad_width=self.current_format.pad_width)
        self._copy_to_clipboard(text)
        self.set_status(f"Copied all {len(self.current_combos)} set(s) to clipboard.")

    def on_copy_selected(self) -> None:
        try:
            selection = self.output.get("sel.first", "sel.last")
        except tk.TclError:
            selection = ""
        if not selection.strip():
            messagebox.showinfo("Nothing selected",
                                "Select one or more lines in the results first.")
            return
        self._copy_to_clipboard(selection)
        self.set_status("Copied selection to clipboard.")

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #
    def _ensure_results(self) -> bool:
        if not self.current_combos:
            messagebox.showinfo("No results", "Generate some numbers first.")
            return False
        return True

    def _copy_to_clipboard(self, text: str) -> None:
        self.master.clipboard_clear()
        self.master.clipboard_append(text)


def launch() -> None:
    """Create the Tk root window and start the event loop."""
    root = tk.Tk()
    root.title(APP_TITLE)
    root.minsize(820, 560)
    root.geometry("900x640")
    LotteryApp(root)
    root.mainloop()
