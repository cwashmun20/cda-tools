"""Dance representation and name/level conversion utilities.

This module provides the Dance class and functions for converting
dance names and levels from spreadsheet input to standard naming conventions.
All constants have been moved to cda_core.lib.constants.
"""

import constants


def convert_dance(style: str, input_name: str) -> str:
    """Converts input dance from entry spreadsheet into a standard naming convention, returning a string.

    Args:
        style: the dance's style/category (e.g. "Smooth", "Latin").
        input_name: the dance's name from spreadsheet input.
    Returns:
        a string with the dance's name, converted to a standard naming convention.
    Raises:
        ValueError: if style is not a recognized style/category.
        ValueError: if input_name is all caps, indicating a multi-dance (e.g. "WTF").
        ValueError: if input_name is not a recognized dance.
    """
    if style not in constants.STYLES:
        raise ValueError(f"""Unrecognized style.
                         Please add support for '{style}' to convert_dance in dance.py""")

    if input_name == "West Coast Swing":
        return constants.DANCE_NAMES[constants.Style.NIGHTCLUB][0]

    if input_name in ("Night Club 2-Step", "Nightclub 2-Step", "Nightclub Two-Step"):
        return constants.DANCE_NAMES[constants.Style.NIGHTCLUB][1]

    if input_name == "Viennese Waltz":
        return "Viennese"

    # Check if dance name is the same as in the standard naming convention.
    if input_name in constants.DANCE_NAMES[style]:
        return input_name

    # Check if dance is abbreviated in standard naming convention.
    for dance_name in constants.DANCE_NAMES[style]:
        if dance_name in input_name:
            return dance_name

    if input_name.isupper():
        raise ValueError("""Attempted to construct a Dance from a multi-dance event.
                            Please handle multi-dance events in the entry checker.""")

    # Unrecognized level name format.
    raise ValueError(f"""Unrecognized dance.
                     Please add support for '{style} {input_name}' to convert_dance in dance.py.""")


def convert_level(input_name: str) -> str:
    """Converts input level from entry spreadsheet into standard naming convention, returning a string.

    Args:
        input_name: the dance's level from spreasheet input (e.g. "Newcomer", "Pre-Championship").
    Returns:
        a string with the the dance's level, converted to a standard naming convention.
    Raises:
        ValueError: if input_name is not a recognized level.
    """
    # Level already matches naming convention; nothing to do here.
    if input_name in constants.ALL_LEVELS:
        return input_name

    # Nightclub Levels
    if input_name in ("Intermediate/Advanced", "Advanced", "Intermediate/Adv.", "Int/Adv"):
        return constants.NC_LEVELS[1]

    # Rookie-Vet Levels
    if input_name in ("Rookie Leader", "Rookie Leaders", "RV Rookie Lead"):
        return constants.RookieVetLevel.ROOKIE_LEAD

    if input_name in ("Rookie Follower", "Rookie Followers", "RV Rookie Follow"):
        return constants.RookieVetLevel.ROOKIE_FOLLOW

    # Open Levels
    if input_name in ("Pre-Champ", "PreChamp"):
        return constants.OPEN_LEVELS[1]

    if input_name in ("Championship",):
        return constants.OPEN_LEVELS[2]

    # Unrecognized level name format.
    raise ValueError(f"""Unrecognized level name.
                     Please add support for '{input_name}' to convert_level in dance.py.""")


class Dance:
    """Represents a dance style at a certain level."""

    level = None
    style = None
    dance = None

    def __init__(self, level: str, style: str, dance: str):
        self.level = convert_level(level)
        self.style = style
        self.dance = convert_dance(style, dance)

    def __repr__(self) -> str:
        designation = ""
        if self.style in constants.AM_STYLES:
            designation = "Am. "
        elif self.style in constants.INTL_STYLES:
            designation = "Intl. "

        return f"{self.level} {designation}{self.dance}"

    def __key(self):
        return (self.level, self.style, self.dance)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other) -> bool:
        if isinstance(other, Dance):
            return self.__key() == other.__key()