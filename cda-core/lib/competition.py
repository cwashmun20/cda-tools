"""Competition representation and entry checking orchestration.

Coordinates the entry checking process using the models, rules,
and parsing layers.
"""

from datetime import date
import pandas as pd
import constants
from models.dance import Dance
from models.dancer import Dancer
from models.entry import Entry
from models.partnership import Partnership
from parsing.csv_reader import read_entries
from parsing.row_parser import is_tba_row
from parsing.multi_dance_expander import expand_multi_dance_events
from rules.level_rules import LevelRulesChecker


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
            df = read_entries(path)

        self.raw_data = expand_multi_dance_events(df)

    def check_entries(self):
        # Check for Proficiency Violations, Newcomer Violations,
        # Nightclub Beginner Violations, and Rookie-Vet Violations.
        for _, row in self.raw_data.iterrows():
            # Ignore TBA rows
            if is_tba_row(row):
                continue

            lead_first, lead_last = row["Lead First"], row["Lead Last"]
            follow_first, follow_last = row["Follow First"], row["Follow Last"]

            partners = []
            for first, last in [(lead_first, lead_last), (follow_first, follow_last)]:
                full_name = first + " " + last
                partners.append(full_name)
                if full_name not in self.competitors:
                    self.competitors[full_name] = Dancer.from_api(
                        curr_comp_date=self.comp_date, first=first, last=last)

            partnership_name = " & ".join(partners)
            lead_obj = self.competitors[partners[0]]
            follow_obj = self.competitors[partners[1]]
            if partnership_name not in self.partnerships:
                self.partnerships[partnership_name] = Partnership(lead_obj, follow_obj)

            partnership_obj = self.partnerships[partnership_name]
            level, style, dance_name = row["Skill"], row["Style"], row["Dance"]
            if "Heat" in self.raw_data.columns:
                heat = row["Heat"]
            else:
                heat = None

            dance_obj = Dance(level, style, dance_name)
            if partnership_obj.eligible(dance_obj, self.rv_ruleset):
                self.entries.add(Entry(dance_obj, partnership_obj, heat))
                # If ineligible, violations will already be printed.

        # Check for Consecutive Level Violations using LevelRulesChecker
        for dancer_obj in list(self.competitors.values()):
            violations = LevelRulesChecker.check(dancer_obj, self.FLC_LEVEL_LIMIT)
            for violation in violations:
                if violation.detail_message:
                    print(violation.detail_message)
                    print()