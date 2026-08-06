"""Competition representation.

Competition is a data model: it holds a competition's identity (name, date,
ruleset) and the raw entry data, plus the competitors/partnerships/entries
accumulated while checking it. It does not parse input, prompt for input,
or check eligibility — see entry_checking.lib.entry_checker.EntryChecker
for that orchestration.
"""

from datetime import date
import pandas as pd

from utils.lib.models.dancer import Dancer
from utils.lib.models.entry import Entry
from utils.lib.models.partnership import Partnership


class Competition:
    """Representation of a CDA competition."""

    def __init__(
        self,
        comp_name: str,
        comp_date: date,
        rv_ruleset: str,
        consecutive_level_limit: int,
        rookie_max_level: str,
        raw_data: pd.DataFrame,
    ):
        """Create a Competition.

        Args:
            comp_name: The competition's name.
            comp_date: The competition's date.
            rv_ruleset: Either "newcomer" or "level", the rookie-vet ruleset
                        this competition uses.
            consecutive_level_limit: The number of allowed consecutive
                              Smooth/Standard/Rhythm/Latin levels.
            rookie_max_level: Either "Bronze" or "Silver" - the highest level
                              a Rookie may also compete at in regular events
                              in that style, under the "newcomer" rv_ruleset.
                              Unused under the "level" rv_ruleset.
            raw_data: The competition's entries, already CSV-parsed and
                      multi-dance-expanded (see utils.lib.parsing).
        """
        self.comp_name = comp_name
        self.comp_date = comp_date
        self.rv_ruleset = rv_ruleset
        self.consecutive_level_limit = consecutive_level_limit
        self.rookie_max_level = rookie_max_level
        self.raw_data = raw_data

        self.competitors: dict[str, Dancer] = {}  # Competitor name keys
        self.partnerships: dict[str, Partnership] = {}  # Partnership name keys
        self.entries: set[Entry] = set()
