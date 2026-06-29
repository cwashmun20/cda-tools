"""Multi-dance event expansion for competition entries.

Handles expanding abbreviated multi-dance events (e.g., "WTQ" → Waltz, Tango, Quickstep)
into individual dance rows for processing.
"""

from typing import Optional

import constants


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


def expand_multi_dance_events(df) -> object:
    """Replaces multi-dance event rows in a DataFrame with one row per dance.

    Identifies multi-dance events by checking if the "Dance" field is
    all uppercase (indicating an abbreviation like "WTQ" or "CSRJ").

    Args:
        df: A pandas DataFrame with competition entry data.
    Returns:
        A new DataFrame with multi-dance events expanded into individual rows.
    """
    import pandas as pd

    data_has_o2cm_name = "O2CM Name" in df.columns
    data_has_heat = "Heat" in df.columns
    row_list = []

    for _, row in df.iterrows():
        dances = row["Dance"]

        # Leave non-multi-dance rows as-is
        if not isinstance(dances, str) or not dances.isupper():
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

        # Handle slashes in abbreviations (e.g., "W/T/Q")
        if '/' in dances:
            dances = ''.join(dances.split('/'))

        dance_names = expand_abbreviation(style, dances)

        for dance_name in dance_names:
            curr_row = [style, dance_name, level, lead_first, lead_last,
                        follow_first, follow_last]
            if data_has_o2cm_name:
                curr_row.append(o2cm_name)
            if data_has_heat:
                curr_row.append(heat)
            row_list.append(curr_row)

    col_names = df.columns.tolist()
    return pd.DataFrame(row_list, columns=col_names)