STYLES = ["Standard", "Smooth", "Latin", "Rhythm", "Nightclub"]
AM_STYLES = ["Smooth", "Rhythm"]
INTL_STYLES = ["Standard", "Latin"]

DANCES = {"Standard": ["Waltz", "Tango", "Viennese", "Foxtrot", "Quickstep"],
          "Smooth": ["Waltz", "Tango", "Foxtrot", "Viennese"],
          "Latin": ["ChaCha", "Samba", "Rumba", "Paso", "Jive"],
          "Rhythm": ["ChaCha", "Rumba", "Swing", "Bolero", "Mambo"],
          "Nightclub": ["WCS", "NC2S", "Lindy", "Merengue", "Blues", "Salsa", "Argentine", "Hustle", "Bachata", "Polka"]}

STANDARD_MAP = {"W": "Waltz",
                "T": "Tango",
                "V": "Viennese",
                "F": "Foxtrot",
                "Q": "Quickstep"}
SMOOTH_MAP = {"W": "Waltz",
              "T": "Tango",
              "F": "Foxtrot",
              "V": "Viennese"}
LATIN_MAP = {"C": "ChaCha",
             "S": "Samba",
             "R": "Rumba",
             "P": "Paso",
             "J": "Jive"}
RHYTHM_MAP = {"C": "ChaCha",
              "R": "Rumba",
              "S": "Swing",
              "B": "Bolero",
              "M": "Mambo"}
ABBREVIATION_MAPS = {"Standard": STANDARD_MAP,
                     "Smooth": SMOOTH_MAP,
                     "Latin": LATIN_MAP,
                     "Rhythm": RHYTHM_MAP}

SYLLABUS_LEVELS = ["Newcomer", "Bronze", "Silver", "Gold"]
OPEN_LEVELS = ["Novice", "Prechamp", "Champ"]
FLC_LEVELS = SYLLABUS_LEVELS + OPEN_LEVELS
NC_LEVELS = ["Beginner", "Int/Adv"]
ALL_LEVELS = FLC_LEVELS + NC_LEVELS + ["Rookie/Vet"]

def flc_fulldancelist():
    """Generates a list of all points-eligible dances at all levels, Newcomer through Champ."""
    fulldancelist = []
    for level in FLC_LEVELS:
        for style in STYLES[:-1]:
            for dance_name in DANCES[style]:
                fulldancelist.append(Dance(style, dance_name, level))
    return fulldancelist


def convert_dance(style, dance):
    """Converts input dance from entry spreadsheet into standard naming convention"""

    if dance == "West Coast Swing":
        return "WCS"

    if dance == "Night Club 2-Step" or dance == "Nightclub 2-Step":
        return "NC2S"

    # Check if dance name is the same as in the standard naming convention.
    if dance in DANCES[style]:
        return dance
    
    # Check if dance is abbreviated in standard naming convention.
    for dance_name in DANCES[style]:
        if dance_name in dance:
            return dance_name

    if dance.isupper():
        raise ValueError("""Attempted to construct a Dance from a multi-dance event. 
                            Please handle multi-dance events in the entry checker.""")
    
class Dance:
    """Representation of a dance style at a certain level."""

    style = None
    dance = None
    level = None

    def __init__(self, style, dance, level):
        self.style = style
        self.dance = convert_dance(style, dance)
        self.level = level
        # self.level = convert_level(style, level)  # TODO (CWA): Implement this to handle data imports.

    
    def __repr__(self):
        designation = ""
        if self.style in AM_STYLES:
            designation = "Am. "
        elif self.style in INTL_STYLES:
            designation = "Intl. "

        return f"{self.level} {designation}{self.dance}"
        