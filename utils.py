"""Helper utilities: formatting, input validation and file export.

Pure functions with no UI dependencies so they can be unit-tested and reused
by both the desktop and web front-ends.
"""
from __future__ import annotations

import csv
import io
from typing import List, Sequence

from generator import MAX_SETS, LotteryFormat

# Visual separator used in the displayed/exported combinations:
#   41 - 03 - 44 - 39 - 08 - 17
SEPARATOR = " - "


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def format_combo(combo: Sequence[int], pad_width: int = 2) -> str:
    """Format one combination, e.g. ``41 - 03 - 44 - 39 - 08 - 17``."""
    return SEPARATOR.join(str(n).zfill(pad_width) for n in combo)


def format_results(
    combos: Sequence[Sequence[int]],
    pad_width: int = 2,
    numbered: bool = True,
) -> str:
    """Format a list of combinations into a multi-line string for display."""
    if not combos:
        return ""
    index_width = len(str(len(combos)))
    lines: List[str] = []
    for idx, combo in enumerate(combos, start=1):
        line = format_combo(combo, pad_width)
        if numbered:
            line = f"{str(idx).rjust(index_width)}.  {line}"
        lines.append(line)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def validate_count(raw: str) -> int:
    """Validate the user-entered number of sets.

    Returns the parsed integer or raises :class:`ValueError` with a friendly
    message suitable for showing in a dialog.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Please enter how many sets to generate.")
    if not raw.isdigit():
        raise ValueError("Number of sets must be a positive whole number.")
    value = int(raw)
    if value < 1:
        raise ValueError("Number of sets must be at least 1.")
    if value > MAX_SETS:
        raise ValueError(f"Number of sets must not exceed {MAX_SETS}.")
    return value


def validate_custom_format(name: str, pick_raw: str, max_raw: str) -> LotteryFormat:
    """Build a :class:`LotteryFormat` from raw custom-format strings."""
    pick_raw = (pick_raw or "").strip()
    max_raw = (max_raw or "").strip()
    if not pick_raw.isdigit():
        raise ValueError("'Numbers per set' must be a positive whole number.")
    if not max_raw.isdigit():
        raise ValueError("'Highest number' must be a positive whole number.")

    pick = int(pick_raw)
    max_number = int(max_raw)
    # LotteryFormat.__post_init__ performs the remaining range validation.
    label = (name or "").strip() or f"{pick}/{max_number}"
    return LotteryFormat(label, pick, max_number)


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def combos_to_txt(combos: Sequence[Sequence[int]], pad_width: int = 2) -> str:
    """Render combinations as the plain-text payload for a .txt export."""
    return format_results(combos, pad_width=pad_width, numbered=True)


def combos_to_csv(combos: Sequence[Sequence[int]], pick: int) -> str:
    """Render combinations as CSV text (header + one row per set)."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Set"] + [f"N{i + 1}" for i in range(pick)])
    for idx, combo in enumerate(combos, start=1):
        writer.writerow([idx, *combo])
    return output.getvalue()
