"""Core lottery combination generation logic.

This module is shared by the Tkinter desktop app and the Flask web app.

Randomness is provided by Python's :mod:`secrets` module (cryptographically
strong) instead of :mod:`random`, giving much stronger unpredictability for the
generated combinations. Numbers within a set are guaranteed unique and are
returned in a *random, unsorted* order.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from math import comb
from typing import List, Set, Tuple

# Hard upper bound on how many sets may be generated in one request.
MAX_SETS = 1000


@dataclass(frozen=True)
class LotteryFormat:
    """Describes a lottery format: pick ``pick`` unique numbers from 1..max_number.

    Examples
    --------
    ``LotteryFormat("6/49", 6, 49)`` -> classic 6-from-49 lottery.
    """

    name: str
    pick: int
    max_number: int

    def __post_init__(self) -> None:
        if self.pick < 1:
            raise ValueError("You must pick at least 1 number.")
        if self.max_number < 1:
            raise ValueError("The maximum number must be at least 1.")
        if self.max_number < self.pick:
            raise ValueError(
                f"The range (1-{self.max_number}) is too small to pick "
                f"{self.pick} unique numbers."
            )

    @property
    def total_combinations(self) -> int:
        """Total count of distinct *unordered* combinations (n choose k)."""
        return comb(self.max_number, self.pick)

    @property
    def pad_width(self) -> int:
        """Digit width used when zero-padding numbers for display."""
        # At least 2 so single-digit numbers render as "03" like the spec example.
        return max(2, len(str(self.max_number)))


# Built-in presets requested in the spec.
PRESETS = {
    "6/49": LotteryFormat("6/49", 6, 49),
    "6/58": LotteryFormat("6/58", 6, 58),
}

DEFAULT_FORMAT = PRESETS["6/49"]


class GenerationError(Exception):
    """Raised when a valid set of combinations cannot be produced."""


class CombinationGenerator:
    """Generates lottery combinations for a given :class:`LotteryFormat`.

    When ``unique=True`` the generator guarantees that no combination is
    repeated for the lifetime of this instance (i.e. across the current
    session). Use :meth:`reset_session` to forget previously seen combos.
    """

    def __init__(self, fmt: LotteryFormat = DEFAULT_FORMAT) -> None:
        self.fmt = fmt
        self._seen: Set[Tuple[int, ...]] = set()

    # ------------------------------------------------------------------ #
    # Session state
    # ------------------------------------------------------------------ #
    def reset_session(self) -> None:
        """Forget every previously generated combination."""
        self._seen.clear()

    @property
    def seen_count(self) -> int:
        return len(self._seen)

    # ------------------------------------------------------------------ #
    # Core drawing
    # ------------------------------------------------------------------ #
    def _draw(self) -> List[int]:
        """Draw ``pick`` unique numbers in random (unsorted) order.

        Implemented as a partial Fisher-Yates shuffle driven entirely by
        :func:`secrets.randbelow`. Consequences:

        * uses cryptographic randomness (the ``secrets`` module),
        * never produces a duplicate number inside the set,
        * the result is in random positions and is **not** sorted.
        """
        n = self.fmt.max_number
        k = self.fmt.pick
        pool = list(range(1, n + 1))
        for i in range(k):
            # pick j uniformly from the remaining [i, n)
            j = i + secrets.randbelow(n - i)
            pool[i], pool[j] = pool[j], pool[i]
        return pool[:k]

    def generate_one(self, unique: bool = False) -> List[int]:
        """Generate a single combination."""
        if not unique:
            return self._draw()

        # Cannot create more unique combos than mathematically exist.
        if len(self._seen) >= self.fmt.total_combinations:
            raise GenerationError(
                "Every possible unique combination for this format has already "
                "been generated this session."
            )

        # Collisions are rare with a large space, but cap attempts to be safe.
        for _ in range(10_000):
            combo = self._draw()
            canonical = tuple(sorted(combo))  # order-independent fingerprint
            if canonical not in self._seen:
                self._seen.add(canonical)
                return combo
        raise GenerationError(
            "Could not find a new unique combination after many attempts."
        )

    def generate_many(self, count: int, unique: bool = False) -> List[List[int]]:
        """Generate ``count`` combinations.

        Raises :class:`GenerationError` on an invalid count or when not enough
        unique combinations remain.
        """
        if count < 1:
            raise GenerationError("Count must be at least 1.")
        if count > MAX_SETS:
            raise GenerationError(f"Count must not exceed {MAX_SETS}.")

        if unique:
            remaining = self.fmt.total_combinations - len(self._seen)
            if count > remaining:
                raise GenerationError(
                    f"Only {remaining} more unique combination(s) are possible "
                    f"for the {self.fmt.name} format."
                )

        return [self.generate_one(unique=unique) for _ in range(count)]
