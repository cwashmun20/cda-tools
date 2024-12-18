from datetime import date
import pandas as pd
import dance
import dancer
import entry
import partnership

def is_tba_row(row) -> bool:
    """Checks whether an entry row is a TBA entry (missing a lead or follow name)."""
    missing_lead = type(row["Lead First"]) == float and type(row["Lead Last"]) == float
    missing_follow = type(row["Follow First"]) == float and type(row["Follow Last"]) == float
    return missing_lead or missing_follow

class Competition:
    """Representation of a CDA competition."""

    raw_data = pd.DataFrame()
    comp_name = "NO COMP NAME PROVIDED"
    comp_date = date(1111, 1, 1)
    competitors = {}  # Competitor name keys, Dancer object values
    partnerships = {}  # Partnership name keys, Partnership object values.
    rv_ruleset = ""
    entries = set()
    FLC_LEVEL_LIMIT = 2  # The number of allowed consecutive Smooth/Standard/Rhythm/Latin levels.

    def __init__(self, path: str = None, df: pd.DataFrame = None):
        self.comp_name = input("Please enter competition name: ")
        # Bypass naming for test purposes (defaults to newcomer rv ruleset).
        if self.comp_name == "test":
            self.comp_date = date.today()
            self.rv_ruleset = "newcomer"
            self.FLC_LEVEL_LIMIT = 2
        else:
            date_str = input("Please enter competition date (MM/DD/YYYY): ")
            month, day, year = date_str.split('/')
            self.comp_date = date(int(year), int(month), int(day))

            rv_ruleset_input = input("Please enter desired rookie-vet ruleset ('newcomer' or 'level'): ")
            if rv_ruleset_input not in ['newcomer', 'level']:
                raise ValueError("Rookie-vet ruleset must be either 'newcomer' or 'level' (without asterisks).")
            self.rv_ruleset = rv_ruleset_input
            
            self.FLC_LEVEL_LIMIT = int(input("Please enter the number of consecutive Smooth/Standard/Rhythm/Latin levels allowed (2 is recommended): "))

        print()  # Add newline after comp setup.

        if not df and not path:
            raise ValueError("""Must provide a path to a .csv file or a dataframe 
                             to construct a Competition object.""")
        if not df and path:
            df = pd.read_csv(path)

        self.raw_data = df
        self.multi_dance_preprocess()

    def multi_dance_preprocess(self):
        """Replaces multi-dance event rows in a competition's raw data with one
        row for each dance in the multi-dance event.
        """
        data_has_heat = "Heat" in self.raw_data.columns
        row_list = []
        for _, row in self.raw_data.iterrows():
            # Ignore TBA rows (should only be checked once the partnership is known
            # in case of Split Level Exception, etc.).
            if is_tba_row(row):
                continue

            dances = row["Dance"]
            # Leave non-multi-dance rows as-is.
            if not dances.isupper():
                row_list.append(row.tolist())
            else:
                # TODO (CWA): Rework this to leverage row.tolist() and then replacing
                #               the dance name in each deep copy of row.tolist() to eliminate
                #               the need for saving most of the data in variables.

                # TODO (CWA): Add support for alternate headers (e.g. "Leader First").
                style = row["Style"]
                level = row["Skill"]
                lead_first = row["Lead First"]
                lead_last = row["Lead Last"]
                follow_first = row["Follow First"]
                follow_last = row["Follow Last"]
                o2cm_name = row["O2CM Name"]
                if data_has_heat:
                    heat = row["Heat"]

                if '/' in dances:
                    dances = ''.join(dances.split('/'))

                for char in dances:
                    dance_name = dance.ABBREVIATION_MAPS[style][char]
                    # TODO(CWA): Eventually, update o2cm name to match each 
                    #               individual dance (unclear if this is important).
                    if data_has_heat:
                        row_list.append([style, dance_name, level, lead_first, lead_last, 
                                        follow_first, follow_last, o2cm_name, heat])
                    else:
                        row_list.append([style, dance_name, level, lead_first, lead_last, 
                                        follow_first, follow_last, o2cm_name])
        
        col_names = self.raw_data.columns.tolist()
        self.raw_data = pd.DataFrame(row_list, columns=col_names)
    
    def check_entries(self):
        # Check for Proficiency Violations, Newcomer Violations,  
        # Nightclub Beginner Violations, and Rookie-Vet Violations.
        for _, row in self.raw_data.iterrows():
            lead_first, lead_last = row["Lead First"], row["Lead Last"]
            follow_first, follow_last = row["Follow First"], row["Follow Last"]

            partners = []
            for first, last in [(lead_first, lead_last), (follow_first, follow_last)]:
                full_name = first + " " + last
                partners.append(full_name)
                if full_name not in self.competitors:
                    self.competitors[full_name] = dancer.Dancer(curr_comp_date=self.comp_date, 
                                                                first=first, last=last)

            partnership_name = " & ".join(partners)
            lead_obj = self.competitors[partners[0]]
            follow_obj = self.competitors[partners[1]]
            if partnership_name not in self.partnerships:
                self.partnerships[partnership_name] = partnership.Partnership(lead_obj, follow_obj)

            partnership_obj = self.partnerships[partnership_name]
            level, style, dance_name = row["Skill"], row["Style"], row["Dance"]
            if "Heat" in self.raw_data.columns:
                heat = row["Heat"]
            else:
                heat = None

            dance_obj = dance.Dance(level, style, dance_name)
            if partnership_obj.eligible(dance_obj, self.rv_ruleset):
                self.entries.add(entry.Entry(dance_obj, partnership_obj, heat))
                # If ineligible, violations will already be printed.
    
        # Check for Consecutive Level Violations
        for dancer_obj in list(self.competitors.values()):
            name = dancer_obj.name
            level_log = {"Smooth": set(),
                         "Standard": set(),
                         "Rhythm": set(),
                         "Latin": set()}
            for entry_obj in dancer_obj.entries:
                style = entry_obj.dance_data.style
                level = entry_obj.dance_data.level
                if style in dance.STYLES and level in dance.FLC_LEVELS:
                    level_log[style].add(dance.FLC_LEVELS.index(level))
            
            for style, level_set in level_log.items():
                # Check for too many levels registered.
                if len(level_set) > self.FLC_LEVEL_LIMIT:
                    print(f"CONSECUTIVE LEVEL VIOLATION: {name} is registered for more than {self.FLC_LEVEL_LIMIT} level(s) of {style}:")
                    for level_number in sorted(level_set):
                        print(f"\t {name} is registered for at least one dance in '{dance.FLC_LEVELS[level_number]} {style}'.")
                    print()
                
                # Check for non-consecutive levels registered.
                else:
                    sorted_levels = sorted(list(level_set))
                    curr_idx, next_idx = 0, 1
                    while next_idx < len(sorted_levels):
                        if sorted_levels[next_idx] - sorted_levels[curr_idx] != 1:
                            level_name_1 = dance.FLC_LEVELS[sorted_levels[curr_idx]]
                            level_name_2 = dance.FLC_LEVELS[sorted_levels[next_idx]]
                            print(f"CONSECUTIVE LEVEL VIOLATION: {name} is registered for at least one event in both '{level_name_1} {style}' and '{level_name_2} {style}'.")
                        curr_idx += 1
                        next_idx += 1