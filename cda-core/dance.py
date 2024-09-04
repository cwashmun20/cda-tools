STYLES = ["Smooth", "Standard", "Rhythm", "Latin", "Nightclub"]
AM_STYLES = ["Smooth", "Rhythm"]
INTL_STYLES = ["Standard", "Latin"]

DANCES = {"Smooth": ["Waltz", "Tango", "Foxtrot", "Viennese"],
          "Standard": ["Waltz", "Tango", "Viennese", "Foxtrot", "Quickstep"],
          "Rhythm": ["ChaCha", "Rumba", "Swing", "Bolero", "Mambo"],
          "Latin": ["ChaCha", "Rumba", "Samba", "Jive", "Paso"],
          "Nightclub": ["WCS", "NC2S", "Lindy", "Merengue", "Blues", "Salsa", "Argentine", "Hustle", "Bachata", "Polka"]}

SMOOTH_MAP = {"W": "Waltz",
              "T": "Tango",
              "F": "Foxtrot",
              "V": "Viennese"}
STANDARD_MAP = {"W": "Waltz",
                "T": "Tango",
                "V": "Viennese",
                "F": "Foxtrot",
                "Q": "Quickstep"}
RHYTHM_MAP = {"C": "ChaCha",
              "R": "Rumba",
              "S": "Swing",
              "B": "Bolero",
              "M": "Mambo"}
LATIN_MAP = {"C": "ChaCha",
             "R": "Rumba",
             "S": "Samba",
             "J": "Jive",
             "P": "Paso"}
ABBREVIATION_MAPS = {"Smooth": SMOOTH_MAP,
                     "Standard": STANDARD_MAP,
                     "Rhythm": RHYTHM_MAP,
                     "Latin": LATIN_MAP}


FLC_LEVELS = ["Newcomer", "Bronze", "Silver", "Gold", "Novice", "Prechamp", "Champ"]
ALL_LEVELS = FLC_LEVELS + ["Beginner", "Int/Adv", "Rookie/Vet"]

def convert_dance(style, dance):
    """Converts input dance from entry spreadsheet into standard naming convention"""
    if dance.isupper():
        raise ValueError("""Attempted to construct a dance from a multi-dance event. 
                            Please use the Event class to handle multi-dance events.""")
    
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

class Dance:
    """Representation of a dance style at a certain level."""

    style = None
    dance = None
    level = None

    def __init__(self, style, dance, level):
        self.style = style
        self.dance = convert_dance(style, dance)
        self.level = convert_level(style, level)  # TODO (CWA): Implement this.

    
    def __repr__(self):
        designation = ""
        if self.style in AM_STYLES:
            designation = "Am. "
        elif self.style in INTL_STYLES:
            designation = "Intl. "

        return f"{self.level} {designation}{self.dance}"
        