# Simply slice STYLES[:-1] to exclude Nightclub
STYLES = ["Standard", "Smooth", "Latin", "Rhythm", "Nightclub"]  
AM_STYLES = ["Smooth", "Rhythm"]
INTL_STYLES = ["Standard", "Latin"]

DANCES = {"Standard": ["Waltz", "Tango", "Viennese", "Foxtrot", "Quickstep"],
          "Smooth": ["Waltz", "Tango", "Foxtrot", "Viennese"],
          "Latin": ["ChaCha", "Samba", "Rumba", "Paso", "Jive"],
          "Rhythm": ["ChaCha", "Rumba", "Swing", "Bolero", "Mambo"],
          "Nightclub": ["WCS", "NC2S", "Lindy", "Merengue", "Blues", "Salsa", 
                        "Argentine", "Hustle", "Bachata", "Polka"]}

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
NC_LEVELS = ["Beginner", "IntAdv"]
ALL_LEVELS = FLC_LEVELS + NC_LEVELS + ["RkLead", "RkFollow"]

def flc_fulldancelist() -> list:
    """Generates a list of all points-eligible dances at all levels, 
    Newcomer through Champ.
    """
    fulldancelist = []
    for level in FLC_LEVELS:
        for style in STYLES[:-1]:
            for dance_name in DANCES[style]:
                fulldancelist.append(Dance(style, dance_name, level))
    return fulldancelist


def convert_dance(style: str, input_name: str) -> str:
    """Converts input dance from entry spreadsheet into a standard 
    naming convention
    """

    if input_name == "West Coast Swing":
        return DANCES["Nightclub"][0]

    if input_name == "Night Club 2-Step" or input_name == "Nightclub 2-Step":
        return DANCES["Nightclub"][1]

    # Check if dance name is the same as in the standard naming convention.
    if input_name in DANCES[style]:
        return input_name
    
    # Check if dance is abbreviated in standard naming convention.
    for dance_name in DANCES[style]:
        if dance_name in input_name:
            return dance_name

    if input_name.isupper():
        raise ValueError("""Attempted to construct a Dance from a multi-dance event. 
                            Please handle multi-dance events in the entry checker.""")
    
    # Unrecognized level name format.
    raise ValueError(f"Unrecognized dance name. 
                     Please add support for {input_name} to convert_dance in dance.py.")
    
def convert_level(input_name: str) -> str:
    """Converts input level from entry spreadsheet into standard naming convention"""

    # Level already matches naming convention; nothing to do here.
    if input_name in ALL_LEVELS:
        return input_name

    # Nightclub Levels
    if input_name in ["Intermediate/Advanced", "Advanced", "Intermediate/Adv."]:
        return NC_LEVELS[1]

    # Rookie-Vet Levels
    if input_name in ["Rookie Leader"]:
        return ALL_LEVELS[-2]
    
    if input_name in ["Rookie Follower"]:
        return ALL_LEVELS[-1]
    
    # Open Levels
    if input_name in ["Pre-Champ"]:
        return OPEN_LEVELS[1]
    
    if input_name in ["Championship"]:
        return OPEN_LEVELS[2]

    # Unrecognized level name format.
    raise ValueError(f"Unrecognized level name. 
                     Please add support for {input_name} to convert_level in dance.py.")
    
class Dance:
    """Representation of a dance style at a certain level."""

    style = None
    dance = None
    level = None

    def __init__(self, style: str, dance: str, level: str):
        self.style = style
        self.dance = convert_dance(style, dance)
        self.level = convert_level(level)

    def __repr__(self):
        designation = ""
        if self.style in AM_STYLES:
            designation = "Am. "
        elif self.style in INTL_STYLES:
            designation = "Intl. "

        return f"{self.level} {designation}{self.dance}"
        