"""Constants and enumerations for CDA Fair Level Certification.

This module centralizes all domain constants used across the cda-tools codebase,
including dance styles, levels, dance names, and abbreviation mappings.

Uses Python 3.11+ StrEnum for streamlined syntax (no .value calls needed).
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
    def flc_styles(cls) -> list["Style"]:
        """Returns styles eligible for FLC points (all except Nightclub)."""
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
    """Syllabus (closed) levels eligible for FLC points."""
    NEWCOMER = "Newcomer"
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"


class OpenLevel(StrEnum):
    """Open levels eligible for FLC points."""
    NOVICE = "Novice"
    PRECHAMP = "Prechamp"
    CHAMP = "Champ"


class NightclubLevel(StrEnum):
    """Nightclub competition levels."""
    BEGINNER = "Beginner"
    INT_ADV = "IntAdv"


class RookieVetLevel(StrEnum):
    """Rookie-Vet special level designations."""
    ROOKIE_LEAD = "RkLead"
    ROOKIE_FOLLOW = "RkFollow"


class Round(StrEnum):
    """Competition round names."""
    FINAL = "Final"
    SEMIFINAL = "Semifinal"
    QUARTERFINAL = "Quarterfinal"
    EIGHTH_FINAL = "1/8 Final"
    SIXTEENTH_FINAL = "1/16 Final"
    THIRTY_SECOND_FINAL = "1/32 Final"


# --- Composite lists (for backward compatibility and sequential access) ---
# StrEnum members work directly as strings, so no .value needed.

STYLES: list[str] = list(Style)
AM_STYLES: list[str] = [Style.SMOOTH, Style.RHYTHM]
INTL_STYLES: list[str] = [Style.STANDARD, Style.LATIN]

SYLLABUS_LEVELS: list[str] = list(SyllabusLevel)
OPEN_LEVELS: list[str] = list(OpenLevel)
FLC_LEVELS: list[str] = SYLLABUS_LEVELS + OPEN_LEVELS
NC_LEVELS: list[str] = list(NightclubLevel)

ALL_LEVELS: list[str] = (
    FLC_LEVELS
    + NC_LEVELS
    + [RookieVetLevel.ROOKIE_LEAD, RookieVetLevel.ROOKIE_FOLLOW]
)

ROUNDS: list[str] = list(Round)


# --- Dance names per style ---
# StrEnum members as dict keys work identically to their string values.

DANCE_NAMES: dict[str, list[str]] = {
    Style.STANDARD: ["Waltz", "Tango", "Viennese", "Foxtrot", "Quickstep"],
    Style.SMOOTH: ["Waltz", "Tango", "Foxtrot", "Viennese"],
    Style.LATIN: ["ChaCha", "Samba", "Rumba", "Paso", "Jive"],
    Style.RHYTHM: ["ChaCha", "Rumba", "Swing", "Bolero", "Mambo"],
    Style.NIGHTCLUB: [
        "WCS", "NC2S", "Lindy", "Merengue", "Blues", "Salsa",
        "Argentine", "Hustle", "Bachata", "Polka",
        "Country 2-Step", "Country Swing",
    ],
}


# --- Abbreviation maps (letter → full name for multi-dance events) ---

_STANDARD_MAP: dict[str, str] = {
    "W": "Waltz",
    "T": "Tango",
    "V": "Viennese",
    "F": "Foxtrot",
    "Q": "Quickstep",
}

_SMOOTH_MAP: dict[str, str] = {
    "W": "Waltz",
    "T": "Tango",
    "F": "Foxtrot",
    "V": "Viennese",
}

_LATIN_MAP: dict[str, str] = {
    "C": "ChaCha",
    "S": "Samba",
    "R": "Rumba",
    "P": "Paso",
    "J": "Jive",
}

_RHYTHM_MAP: dict[str, str] = {
    "C": "ChaCha",
    "R": "Rumba",
    "S": "Swing",
    "B": "Bolero",
    "M": "Mambo",
}

ABBREVIATION_MAPS: dict[str, dict[str, str]] = {
    Style.STANDARD: _STANDARD_MAP,
    Style.SMOOTH: _SMOOTH_MAP,
    Style.LATIN: _LATIN_MAP,
    Style.RHYTHM: _RHYTHM_MAP,
}