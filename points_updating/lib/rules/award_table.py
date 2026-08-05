"""CDA Fair Level Certification point-award table.

Points are awarded per dance based on how many rounds an event ran and
what place a couple earned in it. Events with only one round ("Final
Only") always award zero points, regardless of placement.
"""

# Each value is (danced level, one level below, two-or-more levels below).
_SEMI_FINAL: dict[int, tuple[int, int, int]] = {
    1: (3, 6, 7),
    2: (2, 4, 7),
    3: (1, 2, 7),
    4: (0, 0, 7),
    5: (0, 0, 7),
    6: (0, 0, 7),
}

_QUARTER_OR_MORE: dict[int, tuple[int, int, int]] = {
    1: (3, 6, 7),
    2: (2, 4, 7),
    3: (1, 2, 7),
    4: (1, 2, 7),
    5: (1, 2, 7),
    6: (1, 2, 7),
}


def compute_award(num_rounds: int, place: int) -> tuple[int, int, int]:
    """Returns the (danced level, one level below, two-or-more levels
    below) point award for a placement, given how many rounds the event ran.

    Args:
        num_rounds: Number of rounds the event ran (1 = Final Only,
            2 = Semi-Final, 3+ = Quarter Final or more).
        place: The couple's 1-based placement in the event.
    Returns:
        A 3-tuple of points to award at the danced level, one level below,
        and two-or-more levels below. Unlisted placements (7th+) score
        (0, 0, 0).
    Raises:
        ValueError: if num_rounds < 1.
    """
    if num_rounds < 1:
        raise ValueError(f"num_rounds must be >= 1, got {num_rounds}")
    if num_rounds == 1:
        return (0, 0, 0)
    table = _SEMI_FINAL if num_rounds == 2 else _QUARTER_OR_MORE
    return table.get(place, (0, 0, 0))
