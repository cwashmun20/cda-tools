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

class Dance:
    """Representation of a dance style at a certain level."""

    style = None
    dance = None
    level = None
    o2cm_name = None

    def __init__(self, style, dance, level, o2cm_name):
        self.style = style
        self.dance = self.convert_dance(dance)
        self.level = level
        self.o2cm_name = o2cm_name


    def convert_dance(self, dance):
        """Converts input dance into standard naming convention"""
        if dance.isupper():
            raise ValueError("""Attempted to construct a dance from a multi-dance event. 
                             Please use the Event class to handle multi-dance events.""")
        
        # Check if dance name is the same as in the standard naming convention.
        if dance in DANCES[self.style]:
            return dance
        
        # Check if dance is abbreviated in standard naming convention.
        for dance_name in DANCES[self.style]:
            if dance_name in dance:
                return dance_name
        