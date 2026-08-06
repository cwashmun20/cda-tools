"""Constants and enumerations for CDA Fair Level Certification.

This module centralizes all domain constants used across the cda-tools codebase,
including dance styles, levels, dance names, and abbreviation mappings.
"""

import itertools
from enum import StrEnum
from typing import Literal


class Style(StrEnum):
    """Dance style/category."""

    STANDARD = "Standard"
    SMOOTH = "Smooth"
    LATIN = "Latin"
    RHYTHM = "Rhythm"
    NIGHTCLUB = "Nightclub"

    @classmethod
    def points_eligible_styles(cls) -> list["Style"]:
        """Returns styles eligible for points (all except Nightclub)."""
        return [s for s in cls if s != cls.NIGHTCLUB]

    @classmethod
    def american_styles(cls) -> list["Style"]:
        """Returns American-style categories (Smooth, Rhythm)."""
        return [cls.SMOOTH, cls.RHYTHM]

    @classmethod
    def international_styles(cls) -> list["Style"]:
        """Returns International-style categories (Standard, Latin)."""
        return [cls.STANDARD, cls.LATIN]


class SyllabusLevel(StrEnum):
    """Syllabus (closed) levels eligible for points."""

    NEWCOMER = "Newcomer"
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"


class OpenLevel(StrEnum):
    """Open levels eligible for points."""

    NOVICE = "Novice"
    PRECHAMP = "Prechamp"
    CHAMP = "Champ"


class NightclubLevel(StrEnum):
    """Nightclub competition levels."""

    BEGINNER = "Beginner"
    INT_ADV = "Intermediate/Advanced"


class RookieVetLevel(StrEnum):
    """Rookie-Vet special level designations."""

    ROOKIE_LEAD = "Rookie Lead"
    ROOKIE_FOLLOW = "Rookie Follow"


# Which Rookie-Vet ruleset a competition uses (see EligibilityChecker), and
# the highest level a Rookie may also compete at in regular events under the
# "newcomer" ruleset.
RvRuleset = Literal["newcomer", "level"]
RookieMaxLevel = Literal["Bronze", "Silver"]


class Round(StrEnum):
    """Competition round names."""

    FINAL = "Final"
    SEMIFINAL = "Semifinal"
    QUARTERFINAL = "Quarterfinal"
    EIGHTH_FINAL = "1/8 Final"
    SIXTEENTH_FINAL = "1/16 Final"
    THIRTY_SECOND_FINAL = "1/32 Final"


class DanceName(StrEnum):
    """Individual dance names. Some dances (e.g. Waltz) are danced in more
    than one style; Dance.style is what disambiguates those, not the name
    itself."""

    # Standard / Smooth
    WALTZ = "Waltz"
    TANGO = "Tango"
    VIENNESE_WALTZ = "Viennese Waltz"
    FOXTROT = "Foxtrot"
    QUICKSTEP = "Quickstep"

    # Latin / Rhythm
    CHA_CHA = "Cha Cha"
    RUMBA = "Rumba"
    EAST_COAST_SWING = "East Coast Swing"
    BOLERO = "Bolero"
    MAMBO = "Mambo"
    SAMBA = "Samba"
    PASO_DOBLE = "Paso Doble"
    JIVE = "Jive"

    # Nightclub
    WEST_COAST_SWING = "West Coast Swing"
    NIGHTCLUB_TWO_STEP = "Nightclub Two-Step"
    LINDY_HOP = "Lindy Hop"
    MERENGUE = "Merengue"
    BLUES = "Blues"
    SALSA = "Salsa"
    ARGENTINE_TANGO = "Argentine Tango"
    HUSTLE = "Hustle"
    BACHATA = "Bachata"
    POLKA = "Polka"
    COUNTRY_TWO_STEP = "Country Two-Step"
    COUNTRY_SWING = "Country Swing"


# --- Composite lists (for backward compatibility and sequential access) ---

STYLES: list[str] = list(Style)
AM_STYLES: list[str] = [Style.SMOOTH, Style.RHYTHM]
INTL_STYLES: list[str] = [Style.STANDARD, Style.LATIN]

SYLLABUS_LEVELS: list[str] = list(SyllabusLevel)
OPEN_LEVELS: list[str] = list(OpenLevel)
LEVELS: list[str] = SYLLABUS_LEVELS + OPEN_LEVELS
NC_LEVELS: list[str] = list(NightclubLevel)

ALL_LEVELS: list[str] = (
    LEVELS + NC_LEVELS + [RookieVetLevel.ROOKIE_LEAD, RookieVetLevel.ROOKIE_FOLLOW]
)

ROUNDS: list[str] = list(Round)


# --- Dance names per style ---

DANCE_NAMES: dict[Style, list[str]] = {
    Style.STANDARD: [
        DanceName.WALTZ,
        DanceName.TANGO,
        DanceName.VIENNESE_WALTZ,
        DanceName.FOXTROT,
        DanceName.QUICKSTEP,
    ],
    Style.SMOOTH: [DanceName.WALTZ, DanceName.TANGO, DanceName.FOXTROT, DanceName.VIENNESE_WALTZ],
    Style.LATIN: [
        DanceName.CHA_CHA,
        DanceName.SAMBA,
        DanceName.RUMBA,
        DanceName.PASO_DOBLE,
        DanceName.JIVE,
    ],
    Style.RHYTHM: [
        DanceName.CHA_CHA,
        DanceName.RUMBA,
        DanceName.EAST_COAST_SWING,
        DanceName.BOLERO,
        DanceName.MAMBO,
    ],
    Style.NIGHTCLUB: [
        DanceName.WEST_COAST_SWING,
        DanceName.NIGHTCLUB_TWO_STEP,
        DanceName.LINDY_HOP,
        DanceName.MERENGUE,
        DanceName.BLUES,
        DanceName.SALSA,
        DanceName.ARGENTINE_TANGO,
        DanceName.HUSTLE,
        DanceName.BACHATA,
        DanceName.POLKA,
        DanceName.COUNTRY_TWO_STEP,
        DanceName.COUNTRY_SWING,
    ],
}


# --- Syllabus points column layout ---
# The CDA points database lays syllabus points out as one row per level and
# one column per (style, dance) pair, in Standard -> Smooth -> Latin ->
# Rhythm order (see Points.linear_data()). SYLLABUS_COLUMN_OFFSETS gives each
# style's starting column in that layout.
_SYLLABUS_COLUMN_STYLES: list[Style] = [Style.STANDARD, Style.SMOOTH, Style.LATIN, Style.RHYTHM]
SYLLABUS_COLUMN_OFFSETS: dict[Style, int] = dict(
    zip(
        _SYLLABUS_COLUMN_STYLES,
        itertools.accumulate((len(DANCE_NAMES[s]) for s in _SYLLABUS_COLUMN_STYLES), initial=0),
    )
)


# --- Abbreviation maps (letter → full name for multi-dance events) ---

_STANDARD_MAP: dict[str, str] = {
    "W": DanceName.WALTZ,
    "T": DanceName.TANGO,
    "V": DanceName.VIENNESE_WALTZ,
    "F": DanceName.FOXTROT,
    "Q": DanceName.QUICKSTEP,
}

_SMOOTH_MAP: dict[str, str] = {
    "W": DanceName.WALTZ,
    "T": DanceName.TANGO,
    "F": DanceName.FOXTROT,
    "V": DanceName.VIENNESE_WALTZ,
}

_LATIN_MAP: dict[str, str] = {
    "C": DanceName.CHA_CHA,
    "S": DanceName.SAMBA,
    "R": DanceName.RUMBA,
    "P": DanceName.PASO_DOBLE,
    "J": DanceName.JIVE,
}

_RHYTHM_MAP: dict[str, str] = {
    "C": DanceName.CHA_CHA,
    "R": DanceName.RUMBA,
    "S": DanceName.EAST_COAST_SWING,
    "B": DanceName.BOLERO,
    "M": DanceName.MAMBO,
}

ABBREVIATION_MAPS: dict[Style, dict[str, str]] = {
    Style.STANDARD: _STANDARD_MAP,
    Style.SMOOTH: _SMOOTH_MAP,
    Style.LATIN: _LATIN_MAP,
    Style.RHYTHM: _RHYTHM_MAP,
}


# --- Cross-style proficiency pairings ---
# Maps each points-eligible style to its cross-style counterpart (Standard<->Smooth,
# Latin<->Rhythm).

CROSS_STYLE: dict[Style, Style] = {
    Style.STANDARD: Style.SMOOTH,
    Style.SMOOTH: Style.STANDARD,
    Style.LATIN: Style.RHYTHM,
    Style.RHYTHM: Style.LATIN,
}

# Maps a dance name to the dance name it's paired with in the counterpart
# style, for cross-style proficiency. Most pairs share a name (e.g. Waltz is
# danced in both Standard and Smooth); Jive/East Coast Swing are the one pair
# that doesn't. Dances with no cross-style counterpart (Quickstep, Samba,
# Paso Doble, Bolero, Mambo) are intentionally absent from this map.

CROSS_STYLE_DANCE_PAIRS: dict[str, str] = {
    DanceName.WALTZ: DanceName.WALTZ,
    DanceName.TANGO: DanceName.TANGO,
    DanceName.VIENNESE_WALTZ: DanceName.VIENNESE_WALTZ,
    DanceName.FOXTROT: DanceName.FOXTROT,
    DanceName.CHA_CHA: DanceName.CHA_CHA,
    DanceName.RUMBA: DanceName.RUMBA,
    DanceName.JIVE: DanceName.EAST_COAST_SWING,
    DanceName.EAST_COAST_SWING: DanceName.JIVE,
}
