"""Cascades a placement's point award down through lower levels.

Syllabus events cascade down the same dance only; open events cascade into
every dance in the lower syllabus levels of the same style. See
award_table.compute_award for the per-placement point values being cascaded.
"""

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from cda_core.lib import constants
from cda_core.lib.models.dance import Dance


@dataclass
class PointDelta:
    """Per-cell point deltas, same shape/layout as Points.syllabus_data/open_data."""

    syllabus: np.ndarray
    open: np.ndarray


def build_cascade_delta(dance: Dance, award: tuple[int, int, int]) -> PointDelta:
    """Builds the full syllabus/open point delta for one placement's award.

    Syllabus event points cascade down the same (style, dance) column only.
    Open event points cascade into lower open levels' single column,
    and into every dance in the lower syllabus levels of the same style,
    walking constants.LEVELS' unified index so Novice/Prechamp/Champ
    share one cascade loop.

    Args:
        dance: The (level, style, dance) an event was danced at.
        award: The (danced level, one level below, two-or-more levels below)
            point values from award_table.compute_award (or that tuple
            scaled up for the Split-Level Exception).
    Returns:
        A PointDelta with award cascaded into every affected cell.
    """
    danced, one_below, two_plus = award
    syllabus = np.zeros((4, 19), dtype=int)
    open_ = np.zeros((3, 4), dtype=int)

    if dance.level in constants.SYLLABUS_LEVELS:
        row = constants.SYLLABUS_LEVELS.index(dance.level)
        col = constants.SYLLABUS_COLUMN_OFFSETS[dance.style] + constants.DANCE_NAMES[
            dance.style
        ].index(dance.dance)
        for r, pts in _levels_below(row, danced, one_below, two_plus):
            syllabus[r][col] += pts
    else:
        unified_idx = constants.LEVELS.index(dance.level)
        for r, pts in _levels_below(unified_idx, danced, one_below, two_plus):
            if r < 4:
                start = constants.SYLLABUS_COLUMN_OFFSETS[dance.style]
                end = start + len(constants.DANCE_NAMES[dance.style])
                syllabus[r][start:end] += pts
            else:
                open_[r - 4][constants.STYLES.index(dance.style)] += pts

    return PointDelta(syllabus, open_)


def _levels_below(
    danced_idx: int, danced: int, one_below: int, two_plus: int
) -> Iterator[tuple[int, int]]:
    """Yields (level index, points) pairs for the danced level, the level
    directly below it, and every level two-or-more below it, down to 0.
    """
    if danced:
        yield danced_idx, danced
    if danced_idx - 1 >= 0 and one_below:
        yield danced_idx - 1, one_below
    if two_plus:
        for r in range(danced_idx - 2, -1, -1):
            yield r, two_plus
