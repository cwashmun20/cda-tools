"""Dance representation and name/level conversion utilities.

This module provides the Dance class and functions for converting
dance names and levels from spreadsheet input to standard naming conventions.
All constants have been moved to cda_core.lib.constants.
"""

import difflib
from typing import Optional

from cda_core.lib import constants
from cda_core.lib.constants import DanceName, NightclubLevel, OpenLevel, RookieVetLevel, Style

# Minimum similarity ratio (see difflib.SequenceMatcher.ratio) for a spelling
# variant to be accepted as a match. Chosen to catch case/spacing/punctuation
# differences (e.g. "ChaCha" for "Cha Cha") while staying clear of
# unrelated-but-similarly-shaped names (e.g. "Waltz" vs "Viennese Waltz").
_FUZZY_MATCH_CUTOFF = 0.82


def _fuzzy_match(input_name: str, candidates: list[str]) -> Optional[str]:
    """Finds the closest candidate to input_name, if any is close enough.

    Comparison is case/whitespace-insensitive; the returned value is the
    original candidate (correctly cased), not the input.

    Args:
        input_name: the (already-stripped) raw input to match.
        candidates: the canonical values to match against.
    Returns:
        The matching candidate, or None if nothing is close enough.
    """
    normalized_to_candidate = {c.strip().lower(): c for c in candidates}
    matches = difflib.get_close_matches(
        input_name.lower(), normalized_to_candidate.keys(), n=1, cutoff=_FUZZY_MATCH_CUTOFF
    )
    return normalized_to_candidate[matches[0]] if matches else None


def convert_style(input_name: str) -> Style:
    """Converts input style from entry spreadsheet into standard naming convention,
    returning a Style.

    Args:
        input_name: the dance's style/category from spreadsheet input (e.g. "Standard",
            "Ballroom").
    Returns:
        the style, converted to a standard naming convention.
    Raises:
        ValueError: if input_name is not a recognized style.
    """
    standard_style_aliases = (Style.STANDARD, "Ballroom")

    input_name = input_name.strip()

    if input_name in constants.STYLES:
        return Style(input_name)

    if input_name in standard_style_aliases:
        return Style.STANDARD

    match = _fuzzy_match(input_name, constants.STYLES)
    if match is not None:
        return Style(match)

    raise ValueError(f"""Unrecognized style.
                     Please add support for '{input_name}' to convert_style in dance.py.""")


def convert_dance(style: Style, input_name: str) -> str:
    """Converts input dance from entry spreadsheet into a standard naming convention,
    returning a string.

    Args:
        style: the dance's style/category (e.g. "Smooth", "Latin"). Should already be
            normalized via convert_style.
        input_name: the dance's name from spreadsheet input.
    Returns:
        a string with the dance's name, converted to a standard naming convention.
    Raises:
        ValueError: if style is not a recognized style/category.
        ValueError: if input_name is all caps, indicating a multi-dance (e.g. "WTF").
        ValueError: if input_name is not a recognized dance.
    """
    west_coast_swing_aliases = (DanceName.WEST_COAST_SWING, "WCS")
    nightclub_two_step_aliases = (
        DanceName.NIGHTCLUB_TWO_STEP,
        "Night Club 2-Step",
        "Nightclub 2-Step",
        "NC2S",
    )
    argentine_tango_aliases = (DanceName.ARGENTINE_TANGO, "Arg. Tango")
    # "Swing" is a common organizer shorthand for Rhythm's East Coast Swing -
    # checked below with a style == RHYTHM guard, since "Swing" alone is too
    # generic a word to safely alias for every style (e.g. Nightclub also
    # has "West Coast Swing" and "Country Swing").
    rhythm_east_coast_swing_aliases = (DanceName.EAST_COAST_SWING, "Swing")

    if style not in constants.STYLES:
        raise ValueError(f"""Unrecognized style.
                         Please add support for '{style}' to convert_dance in dance.py""")

    input_name = input_name.strip()

    if input_name in west_coast_swing_aliases:
        return DanceName.WEST_COAST_SWING

    if input_name in nightclub_two_step_aliases:
        return DanceName.NIGHTCLUB_TWO_STEP

    if input_name in argentine_tango_aliases:
        return DanceName.ARGENTINE_TANGO

    if style == Style.RHYTHM and input_name in rhythm_east_coast_swing_aliases:
        return DanceName.EAST_COAST_SWING

    # Check if dance name is the same as in the standard naming convention.
    if input_name in constants.DANCE_NAMES[style]:
        return input_name

    # Check if dance is abbreviated in standard naming convention. Longer
    # names are checked first so a more specific name (e.g. "Viennese Waltz")
    # is matched before a shorter one that happens to be its substring
    # (e.g. "Waltz").
    for dance_name in sorted(constants.DANCE_NAMES[style], key=len, reverse=True):
        if dance_name in input_name:
            return dance_name

    if input_name.isupper():
        raise ValueError("""Attempted to construct a Dance from a multi-dance event.
                            Please handle multi-dance events in the entry checker.""")

    # Catch near-miss spellings/formatting not covered by an explicit alias
    # or substring match above (e.g. "ChaCha" for "Cha Cha").
    match = _fuzzy_match(input_name, constants.DANCE_NAMES[style])
    if match is not None:
        return match

    # Unrecognized dance name format.
    raise ValueError(f"""Unrecognized dance.
                     Please add support for '{style} {input_name}' to convert_dance in dance.py.""")


def convert_level(input_name: str) -> str:
    """Converts input level from entry spreadsheet into standard naming convention,
    returning a string.

    Args:
        input_name: the dance's level from spreasheet input (e.g. "Newcomer", "Pre-Championship").
    Returns:
        a string with the the dance's level, converted to a standard naming convention.
    Raises:
        ValueError: if input_name is not a recognized level.
    """
    int_adv_level_aliases = (
        NightclubLevel.INT_ADV,
        "Intermediate/Advanced",
        "Advanced",
        "Intermediate/Adv.",
        "Int/Adv",
    )
    rookie_lead_aliases = (
        RookieVetLevel.ROOKIE_LEAD,
        "Rookie Leader",
        "Rookie Leaders",
        "RV Rookie Lead",
        "R/V Rookie Lead",
    )
    rookie_follow_aliases = (
        RookieVetLevel.ROOKIE_FOLLOW,
        "Rookie Follower",
        "Rookie Followers",
        "RV Rookie Follow",
        "R/V Rookie Follow",
    )
    prechamp_aliases = (OpenLevel.PRECHAMP, "Pre-Champ", "PreChamp")
    champ_aliases = (OpenLevel.CHAMP, "Championship")

    input_name = input_name.strip()

    # Level already matches naming convention; nothing to do here.
    if input_name in constants.ALL_LEVELS:
        return input_name

    # Strip a "Closed " prefix (e.g. "Closed Bronze") some organizers use for
    # syllabus levels.
    if input_name.startswith("Closed "):
        stripped = input_name.removeprefix("Closed ").strip()
        if stripped in constants.ALL_LEVELS:
            return stripped

    # Nightclub Levels
    if input_name in int_adv_level_aliases:
        return NightclubLevel.INT_ADV

    # Rookie-Vet Levels
    if input_name in rookie_lead_aliases:
        return RookieVetLevel.ROOKIE_LEAD

    if input_name in rookie_follow_aliases:
        return RookieVetLevel.ROOKIE_FOLLOW

    # Open Levels
    if input_name in prechamp_aliases:
        return OpenLevel.PRECHAMP

    if input_name in champ_aliases:
        return OpenLevel.CHAMP

    # Catch near-miss spellings/formatting not covered by an explicit alias
    # above (e.g. differing case or punctuation).
    match = _fuzzy_match(input_name, constants.ALL_LEVELS)
    if match is not None:
        return match

    # Unrecognized level name format.
    raise ValueError(f"""Unrecognized level name.
                     Please add support for '{input_name}' to convert_level in dance.py.""")


class Dance:
    """Represents a dance style at a certain level."""

    def __init__(self, level: str, style: str, dance: str):
        self.level: str = convert_level(level)
        self.style: Style = convert_style(style)
        self.dance: str = convert_dance(self.style, dance)

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
        return False
