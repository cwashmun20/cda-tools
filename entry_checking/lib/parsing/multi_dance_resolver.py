"""Multi-dance event dance-name resolution for competition entries.

Resolves a competition entry row's Dance/Style fields into the individual
dance name(s) it covers - a single-item list for an already-single-dance
row, or multiple names for a multi-dance combo written as either letter
abbreviations (e.g. "WTQ" -> Waltz, Tango, Quickstep) or comma-separated
full names (e.g. "Waltz,Tango,Foxtrot,Viennese Waltz").
"""

from typing import Any

from utils.lib import constants
from utils.lib.models.dance import convert_style
from utils.lib.multi_dance import expand_abbreviation


def resolve_dance_names(dances_raw: Any, style_raw: Any) -> list[str]:
    """Resolves one entry row's Dance/Style fields into its dance name(s).

    Args:
        dances_raw: The row's raw "Dance" field value.
        style_raw: The row's raw "Style" field value.
    Returns:
        A single-item list with the original value for an already-single-
        dance row, or the combo's individual dance names for a multi-dance
        row.
    """
    dances = dances_raw
    if isinstance(dances, str):
        dances = dances.strip()

    normalized_style = convert_style(style_raw) if isinstance(style_raw, str) else style_raw

    if isinstance(dances, str) and "," in dances:
        # Already full names (e.g. "Cha Cha,Rumba,East Coast Swing");
        # no abbreviation expansion needed, just split them out.
        return [d.strip() for d in dances.split(",")]

    if (
        isinstance(dances, str)
        and dances.isupper()
        and normalized_style in constants.ABBREVIATION_MAPS
    ):
        # Styles with no abbreviation map (e.g. Nightclub) never have a
        # multi-dance notation - an all-caps value there is a single
        # dance's own abbreviated name (e.g. "WCS", "NC2S"), not a
        # multi-dance code, so it falls through to the pass-through
        # branch below and gets resolved by convert_dance()'s aliases.
        if "/" in dances:
            dances = "".join(dances.split("/"))
        return expand_abbreviation(normalized_style, dances)

    return [dances_raw]
