"""Entry checking orchestration and CLI for CDA Fair Level Certification.

Usage:
    python -m entry_checking.lib.entry_checker

    (or via installed entry point: entry-checker)
"""

from datetime import date
from typing import Optional

from entry_checking.lib.parsing.csv_reader import read_entries
from entry_checking.lib.parsing.multi_dance_resolver import resolve_dance_names
from entry_checking.lib.parsing.row_parser import is_tba_row
from entry_checking.lib.report_view import build_report_view
from entry_checking.lib.rules.eligibility_checker import EligibilityChecker
from entry_checking.lib.rules.level_rules_checker import LevelRulesChecker
from entry_checking.lib.rules.violations import EligibilityResult, LevelViolation
from utils.lib import competition
from utils.lib.constants import RookieVetLevel, SyllabusLevel
from utils.lib.models.dance import Dance
from utils.lib.models.dancer import Dancer
from utils.lib.models.entry import Entry
from utils.lib.models.partnership import Partnership


class EntryChecker:
    """Runs eligibility and level-rule checks over a Competition's entries.

    Builds Dancer/Partnership/Entry objects from a Competition's raw data,
    checks each entry's eligibility, and checks each dancer for consecutive
    level violations. Registers eligible entries onto the competition's
    dancers/partnerships/entries as a side effect. Does not print directly —
    returns structured results for the caller to format.

    check_entry() and register_entry() operate on a single partnership/dance
    pair and are the building blocks check() is written in terms of — they're
    also what a future live-registration caller would call directly, one
    entry at a time. Such a caller needs to submit Rookie/Vet entries last,
    for the same reason check() does — see check()'s docstring.
    """

    def __init__(self, comp: "competition.Competition"):
        self.comp = comp
        self.eligibility_checker = EligibilityChecker(comp.rv_ruleset, comp.rookie_max_level)
        # Level violations already surfaced for a dancer, keyed by
        # (style, violation_type, levels) — lets register_entry() report each
        # violation once, at the entry that first causes it, instead of again
        # on every later entry that happens to still trigger it.
        self._seen_level_violations: dict[str, set[tuple]] = {}

    def check_entry(
        self,
        partnership_obj: Partnership,
        dance_obj: Dance,
        event_dances: Optional[tuple[Dance, ...]] = None,
    ) -> EligibilityResult:
        """Check whether a partnership would be eligible for a dance, without
        registering the entry. Read-only: does not modify the competition,
        partnership, or dancer state.
        """
        return self.eligibility_checker.check(partnership_obj, dance_obj, event_dances)

    def register_entry(
        self,
        partnership_obj: Partnership,
        dance_obj: Dance,
        heat: str | None = None,
        event_dances: Optional[tuple[Dance, ...]] = None,
    ) -> tuple[EligibilityResult, list[LevelViolation]]:
        """Check whether a partnership is eligible for a dance and, if so,
        register the entry and check the lead and follow for any new
        consecutive-level violations.

        Args:
            partnership_obj: The partnership entering the dance.
            dance_obj: The dance being entered.
            heat: The heat number/label, if known.
            event_dances: Every dance in dance_obj's event, for a multi-
                dance event - see EligibilityChecker.check() for how this
                affects the Split-Level Exception/proficiency check.
                Defaults to (dance_obj,) for a single-dance event.
        Returns:
            A tuple of (eligibility_result, new_level_violations).
            new_level_violations contains only violations for the lead/follow
            that weren't already surfaced by an earlier entry — a caller
            doing live registration sees exactly what this entry changed.
            Nothing is registered, and no new level violations are returned,
            if the entry is ineligible.
        """
        result = self.eligibility_checker.check(partnership_obj, dance_obj, event_dances)
        if not result.eligible:
            return result, []

        self.comp.entries.add(Entry(dance_obj, partnership_obj, heat))

        new_violations: list[LevelViolation] = []
        for dancer_obj in (partnership_obj.lead, partnership_obj.follow):
            seen = self._seen_level_violations.setdefault(dancer_obj.name, set())
            for violation in LevelRulesChecker.check(dancer_obj, self.comp.consecutive_level_limit):
                key = (
                    violation.style,
                    violation.dance,
                    violation.violation_type,
                    tuple(violation.levels),
                )
                if key not in seen:
                    seen.add(key)
                    new_violations.append(violation)

        return result, new_violations

    def check(self) -> tuple[list[EligibilityResult], list[LevelViolation]]:
        """Check all of the competition's entries.

        Rookie/Vet entries are registered after every other entry,
        regardless of their row order in the source data - the "newcomer"
        ruleset's Rookie/Vet checks look at a dancer's *other* entries in
        that style (e.g. whether the Rookie also has a regular-level entry,
        or the Veteran is registered for a Bronze/Newcomer event), so those
        other entries need to already be registered for the check to see
        an accurate, order-independent picture.

        Returns:
            A tuple of (eligibility_results, level_violations).
            eligibility_results includes every ineligible entry and every
            split-level exception (both carry a message worth reporting);
            fully-eligible, non-split-level entries aren't included.
        """
        comp = self.comp
        eligibility_results: list[EligibilityResult] = []
        level_violations: list[LevelViolation] = []

        regular_entries = []
        rookie_vet_entries = []

        for _, row in comp.raw_data.iterrows():
            if is_tba_row(row):
                continue

            lead_first, lead_last = row["Lead First"], row["Lead Last"]
            follow_first, follow_last = row["Follow First"], row["Follow Last"]

            partners = []
            for first, last in [(lead_first, lead_last), (follow_first, follow_last)]:
                full_name = first + " " + last
                partners.append(full_name)
                if full_name not in comp.competitors:
                    comp.competitors[full_name] = Dancer.from_api(
                        curr_comp_date=comp.comp_date, first=first, last=last
                    )

            partnership_name = " & ".join(partners)
            lead_obj = comp.competitors[partners[0]]
            follow_obj = comp.competitors[partners[1]]
            if partnership_name not in comp.partnerships:
                comp.partnerships[partnership_name] = Partnership(lead_obj, follow_obj)

            partnership_obj = comp.partnerships[partnership_name]
            level, style = row["Skill"], row["Style"]
            heat = row["Heat"] if "Heat" in comp.raw_data.columns else None

            dance_names = resolve_dance_names(row["Dance"], style)
            event_dances = tuple(Dance(level, style, name) for name in dance_names)
            for dance_obj in event_dances:
                if dance_obj.level in (RookieVetLevel.ROOKIE_LEAD, RookieVetLevel.ROOKIE_FOLLOW):
                    rookie_vet_entries.append((partnership_obj, dance_obj, heat, event_dances))
                else:
                    regular_entries.append((partnership_obj, dance_obj, heat, event_dances))

        for partnership_obj, dance_obj, heat, event_dances in regular_entries + rookie_vet_entries:
            result, new_violations = self.register_entry(
                partnership_obj, dance_obj, heat, event_dances
            )

            if not result.eligible or result.is_split_level:
                eligibility_results.append(result)
            level_violations.extend(new_violations)

        return eligibility_results, level_violations


def _report(
    eligibility_results: list[EligibilityResult], level_violations: list[LevelViolation]
) -> None:
    """Print split-level exception notes, then every other violation grouped
    by whoever it's about (partnership or individual dancer).

    Split-level exceptions aren't violations - they're eligible entries that
    just need a 3x-points note - so they're printed as their own block up
    front rather than grouped in with the real violations. Each group is
    printed under a header naming its subject - the same per-person/couple
    headers the web UI's results page and .txt download use.
    """
    view = build_report_view(eligibility_results, level_violations)

    for note in view.split_level_notes:
        print(note)
        print()

    for subject_name, messages in view.groups:
        print(subject_name)
        for message in messages:
            print(message)
            print()


def main():
    """Run the entry checker, prompting for a CSV file and competition details."""
    path = input("Please enter full path of entry spreadsheet (with file extension): ")
    raw_data = read_entries(path)

    comp_name = input("Please enter competition name: ")
    # Bypass naming for test purposes (defaults to newcomer rv ruleset).
    if comp_name == "test":
        comp_date = date.today()
        rv_ruleset = "newcomer"
        consecutive_level_limit = 2
        rookie_max_level = "Bronze"
    else:
        date_str = input("Please enter competition date (MM/DD/YYYY): ")
        month, day, year = date_str.split("/")
        comp_date = date(int(year), int(month), int(day))

        rv_ruleset = input("Please enter desired rookie-vet ruleset ('newcomer' or 'level'): ")
        if rv_ruleset not in ("newcomer", "level"):
            raise ValueError(
                "Rookie-vet ruleset must be either 'newcomer' or 'level' (without asterisks)."
            )

        if rv_ruleset == "newcomer":
            rookie_max_level = input(
                "Please enter the highest level a Rookie may also compete at in "
                "regular events in that style ('Bronze' or 'Silver'): "
            )
            if rookie_max_level not in (SyllabusLevel.BRONZE, SyllabusLevel.SILVER):
                raise ValueError(
                    "Rookie max level must be either 'Bronze' or 'Silver' (without asterisks)."
                )
        else:
            rookie_max_level = "Bronze"  # unused under the "level" ruleset

        consecutive_level_limit = int(
            input(
                "Please enter the number of consecutive Smooth/Standard/Rhythm/Latin "
                "levels allowed (2 is recommended): "
            )
        )

    print()  # Add newline after comp setup.

    comp = competition.Competition(
        comp_name, comp_date, rv_ruleset, consecutive_level_limit, rookie_max_level, raw_data
    )
    eligibility_results, level_violations = EntryChecker(comp).check()
    _report(eligibility_results, level_violations)


if __name__ == "__main__":
    main()
