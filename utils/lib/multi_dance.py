"""Multi-dance abbreviation expansion for CDA Fair Level Certification.

Shared by entry_checking (expanding a multi-dance CSV row into one row per
dance) and points_updating's O2CM parser (expanding a multi-dance heat name
like "(WTFVCRSBM)" into its constituent dances).
"""

from utils.lib import constants
from utils.lib.constants import Style


def expand_abbreviation(style: Style, abbreviation: str) -> list[str]:
    """Expand a multi-dance abbreviation into individual dance names.

    Args:
        style: The dance style (e.g. "Standard", "Smooth").
        abbreviation: The abbreviation string (e.g. "WTQ", "FV", "CSR").
    Returns:
        A list of full dance names.
    Raises:
        ValueError: If the style has no abbreviation map.
    """
    if style not in constants.ABBREVIATION_MAPS:
        raise ValueError(
            f"No abbreviation map found for style '{style}'. "
            f"Supported styles: {list(constants.ABBREVIATION_MAPS.keys())}"
        )

    abbrev_map = constants.ABBREVIATION_MAPS[style]
    dances = []
    for char in abbreviation:
        if char in abbrev_map:
            dances.append(abbrev_map[char])
        else:
            # Keep unknown characters as-is (they may be partial names)
            dances.append(char)
    return dances
