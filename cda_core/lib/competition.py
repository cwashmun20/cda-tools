"""Competition representation.

Competition is a data model: it holds a competition's identity (name, date,
ruleset) and the raw entry data, plus the competitors/partnerships/entries
accumulated while checking it. It does not parse input, prompt for input,
or check eligibility — see flc_entry_checking.lib.entry_checker.EntryChecker
for that orchestration.
"""

from datetime import date
import pandas as pd


class Competition:
    """Representation of a CDA competition."""

    def __init__(
        self,
        comp_name: str,
        comp_date: date,
        rv_ruleset: str,
        flc_level_limit: int,
        raw_data: pd.DataFrame,
    ):
        """Create a Competition.

        Args:
            comp_name: The competition's name.
            comp_date: The competition's date.
            rv_ruleset: Either "newcomer" or "level", the rookie-vet ruleset
                        this competition uses.
            flc_level_limit: The number of allowed consecutive
                              Smooth/Standard/Rhythm/Latin levels.
            raw_data: The competition's entries, already CSV-parsed and
                      multi-dance-expanded (see cda_core.lib.parsing).
        """
        self.comp_name = comp_name
        self.comp_date = comp_date
        self.rv_ruleset = rv_ruleset
        self.flc_level_limit = flc_level_limit
        self.raw_data = raw_data

        self.competitors = {}  # Competitor name keys, Dancer object values
        self.partnerships = {}  # Partnership name keys, Partnership object values.
        self.entries = set()
