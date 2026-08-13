"""Cascades a placement's point award down through lower levels.

Syllabus events cascade down the same dance only - but a multi-dance
syllabus combo's one overall placement cascades identically into every
dance in the combo, not just one. Open events cascade into every dance in
the lower syllabus levels of the same style regardless of how many dances
the combo covered. See award_table.compute_award for the per-placement
point values being cascaded.
"""

from dataclasses import dataclass
from typing import Iterator

import numpy as np

from utils.lib import constants
from utils.lib.models.dance import Dance


@dataclass
class PointDelta:
    """Per-cell point deltas, same shape/layout as Points.syllabus_data/open_data."""

    syllabus: np.ndarray
    open: np.ndarray


def build_cascade_delta(dances: tuple[Dance, ...], award: tuple[int, int, int]) -> PointDelta:
    """Builds the full syllabus/open point delta for one placement's award.

    Syllabus event points cascade down each dance's own (style, dance)
    column - one dance for a single-dance event, or the same award into
    every dance's own column for a multi-dance combo (the couple's one
    overall placement earns the same points in each contained dance, per
    CDA rules). Open event points cascade into lower open levels' single
    column, and into every dance in the lower syllabus levels of the same
    style, walking constants.LEVELS' unified index so Novice/Prechamp/Champ
    share one cascade loop - already style-wide regardless of how many
    dances the combo covered, so only dances[0] is ever consulted there.

    Args:
        dances: Every dance in the event - a 1-tuple for a single-dance
            event, every dance in the combo for a multi-dance one. All
            share the same (level, style); only the specific dance name
            varies.
        award: The (danced level, one level below, two-or-more levels below)
            point values from award_table.compute_award (or that tuple
            scaled up for the Split-Level Exception).
    Returns:
        A PointDelta with award cascaded into every affected cell.
    """
    danced, one_below, two_plus_below = award
    syllabus = np.zeros((4, 19), dtype=int)
    open_ = np.zeros((3, 4), dtype=int)

    representative = dances[0]
    if representative.level in constants.SYLLABUS_LEVELS:
        row = constants.SYLLABUS_LEVELS.index(representative.level)
        style_offset = constants.SYLLABUS_COLUMN_OFFSETS[representative.style]
        for dance in dances:
            col = style_offset + constants.DANCE_NAMES[dance.style].index(dance.dance)
            for r, pts in _levels_below(row, danced, one_below, two_plus_below):
                syllabus[r][col] += pts
    else:
        unified_idx = constants.LEVELS.index(representative.level)
        for r, pts in _levels_below(unified_idx, danced, one_below, two_plus_below):
            if r < 4:
                start = constants.SYLLABUS_COLUMN_OFFSETS[representative.style]
                end = start + len(constants.DANCE_NAMES[representative.style])
                syllabus[r][start:end] += pts
            else:
                open_[r - 4][constants.STYLES.index(representative.style)] += pts

    return PointDelta(syllabus, open_)


def _levels_below(
    danced_idx: int, danced: int, one_below: int, two_plus_below: int
) -> Iterator[tuple[int, int]]:
    """Yields (level index, points) pairs for the danced level, the level
    directly below it, and every level two-or-more below it, down to 0.
    """
    if danced:
        yield danced_idx, danced
    if danced_idx - 1 >= 0 and one_below:
        yield danced_idx - 1, one_below
    if two_plus_below:
        for r in range(danced_idx - 2, -1, -1):
            yield r, two_plus_below
