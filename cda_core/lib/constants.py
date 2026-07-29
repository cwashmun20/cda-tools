"""Constants and enumerations for CDA Fair Level Certification.

This module centralizes all domain constants used across the cda-tools codebase,
including dance styles, levels, dance names, and abbreviation mappings.
"""

from enum import StrEnum


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


class Round(StrEnum):
    """Competition round names."""

    FINAL = "Final"
    SEMIFINAL = "Semifinal"
    QUARTERFINAL = "Quarterfinal"
    EIGHTH_FINAL = "1/8 Final"
    SIXTEENTH_FINAL = "1/16 Final"
    THIRTY_SECOND_FINAL = "1/32 Final"


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

DANCE_NAMES: dict[str, list[str]] = {
    Style.STANDARD: ["Waltz", "Tango", "Viennese Waltz", "Foxtrot", "Quickstep"],
    Style.SMOOTH: ["Waltz", "Tango", "Foxtrot", "Viennese Waltz"],
    Style.LATIN: ["Cha Cha", "Samba", "Rumba", "Paso Doble", "Jive"],
    Style.RHYTHM: ["Cha Cha", "Rumba", "East Coast Swing", "Bolero", "Mambo"],
    Style.NIGHTCLUB: [
        "West Coast Swing",
        "Nightclub Two-Step",
        "Lindy Hop",
        "Merengue",
        "Blues",
        "Salsa",
        "Argentine Tango",
        "Hustle",
        "Bachata",
        "Polka",
        "Country Two-Step",
        "Country Swing",
    ],
}


# --- Abbreviation maps (letter → full name for multi-dance events) ---

_STANDARD_MAP: dict[str, str] = {
    "W": "Waltz",
    "T": "Tango",
    "V": "Viennese Waltz",
    "F": "Foxtrot",
    "Q": "Quickstep",
}

_SMOOTH_MAP: dict[str, str] = {
    "W": "Waltz",
    "T": "Tango",
    "F": "Foxtrot",
    "V": "Viennese Waltz",
}

_LATIN_MAP: dict[str, str] = {
    "C": "Cha Cha",
    "S": "Samba",
    "R": "Rumba",
    "P": "Paso Doble",
    "J": "Jive",
}

_RHYTHM_MAP: dict[str, str] = {
    "C": "Cha Cha",
    "R": "Rumba",
    "S": "East Coast Swing",
    "B": "Bolero",
    "M": "Mambo",
}

ABBREVIATION_MAPS: dict[str, dict[str, str]] = {
    Style.STANDARD: _STANDARD_MAP,
    Style.SMOOTH: _SMOOTH_MAP,
    Style.LATIN: _LATIN_MAP,
    Style.RHYTHM: _RHYTHM_MAP,
}


# --- Cross-style proficiency pairings ---
# Maps each points-eligible style to its cross-style counterpart (Standard<->Smooth,
# Latin<->Rhythm).

CROSS_STYLE: dict[str, str] = {
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
    "Waltz": "Waltz",
    "Tango": "Tango",
    "Viennese Waltz": "Viennese Waltz",
    "Foxtrot": "Foxtrot",
    "Cha Cha": "Cha Cha",
    "Rumba": "Rumba",
    "Jive": "East Coast Swing",
    "East Coast Swing": "Jive",
}
