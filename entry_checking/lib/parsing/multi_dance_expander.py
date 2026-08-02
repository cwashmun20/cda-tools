"""Multi-dance event expansion for competition entries.

Handles expanding abbreviated multi-dance events (e.g., "WTQ" → Waltz, Tango, Quickstep)
into individual dance rows for processing.
"""

import pandas as pd

from cda_core.lib import constants
from cda_core.lib.models.dance import convert_style


def expand_abbreviation(style: str, abbreviation: str) -> list[str]:
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


def expand_multi_dance_events(df: pd.DataFrame) -> pd.DataFrame:
    """Replaces multi-dance event rows in a DataFrame with one row per dance.

    Identifies multi-dance events in either of two formats:
    - Letter abbreviations, e.g. "WTQ" or "CSRJ" (detected via all-uppercase).
    - Comma-separated full names, e.g. "Waltz,Tango,Foxtrot,Viennese Waltz".

    Args:
        df: A pandas DataFrame with competition entry data.
    Returns:
        A new DataFrame with multi-dance events expanded into individual rows.
    """
    data_has_o2cm_name = "O2CM Name" in df.columns
    data_has_heat = "Heat" in df.columns
    row_list = []

    for _, row in df.iterrows():
        dances = row["Dance"]
        if isinstance(dances, str):
            dances = dances.strip()

        normalized_style = (
            convert_style(row["Style"]) if isinstance(row["Style"], str) else row["Style"]
        )

        if isinstance(dances, str) and "," in dances:
            # Already full names (e.g. "Cha Cha,Rumba,East Coast Swing");
            # no abbreviation expansion needed, just split them out.
            dance_names = [d.strip() for d in dances.split(",")]
        elif (
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
            dance_names = expand_abbreviation(normalized_style, dances)
        else:
            # Leave non-multi-dance rows as-is
            row_list.append(row.tolist())
            continue

        style = row["Style"]
        level = row["Skill"]
        lead_first = row["Lead First"]
        lead_last = row["Lead Last"]
        follow_first = row["Follow First"]
        follow_last = row["Follow Last"]
        o2cm_name = row.get("O2CM Name") if data_has_o2cm_name else None
        heat = row.get("Heat") if data_has_heat else None

        for dance_name in dance_names:
            curr_row = [style, dance_name, level, lead_first, lead_last, follow_first, follow_last]
            if data_has_o2cm_name:
                curr_row.append(o2cm_name)
            if data_has_heat:
                curr_row.append(heat)
            row_list.append(curr_row)

    col_names = df.columns.tolist()
    return pd.DataFrame(row_list, columns=col_names)
