"""Integration tests for entry_checking.lib.entry_checker.

Exercises the full Competition + EntryChecker pipeline together, rather than
each rules/parsing module in isolation.
"""

import contextlib
import io
import unittest
import datetime
import numpy as np
import pandas as pd

from entry_checking.lib.entry_checker import EntryChecker, _report
from entry_checking.lib.rules.violations import EligibilityResult, LevelViolation, ViolationType
from utils.lib import competition
from utils.lib.api.client import DancerRecord
from utils.lib.models.dance import Dance
from utils.lib.models.dancer import Dancer
from utils.lib.models.partnership import Partnership


def _mock_dancer(comp_date, first, last):
    """Build an experienced (>1yr), zero-points Dancer without hitting the API."""
    record = DancerRecord(
        cda_id=1,
        first=first,
        last=last,
        first_comp_date=datetime.date(2020, 1, 1),
        created_date="2020-01-01",
        syllabus_pts=np.zeros((4, 19), dtype=int),
        open_pts=np.zeros((3, 4), dtype=int),
    )
    return Dancer.from_data(comp_date, record)


class TestEntryCheckerPipeline(unittest.TestCase):
    """Tests running EntryChecker over a full Competition."""

    def setUp(self):
        self.comp_date = datetime.date(2026, 6, 1)
        raw_data = pd.DataFrame(
            {
                "Style": ["Smooth", "Smooth", "Smooth", "Smooth", "Smooth"],
                "Dance": ["Waltz", "Waltz", "Waltz", "Tango", "Waltz"],
                "Skill": ["Bronze", "Silver", "Gold", "Newcomer", "Bronze"],
                "Lead First": ["Baris", "Baris", "Baris", "Baris", "Baris"],
                "Lead Last": ["Varol", "Varol", "Varol", "Varol", "Varol"],
                "Follow First": ["Denise", "Denise", "Denise", "Denise", np.nan],  # last row is TBA
                "Follow Last": ["Machin", "Machin", "Machin", "Machin", np.nan],
            }
        )
        self.comp = competition.Competition(
            comp_name="test",
            comp_date=self.comp_date,
            rv_ruleset="newcomer",
            consecutive_level_limit=2,
            rookie_max_level="Bronze",
            raw_data=raw_data,
        )
        # Pre-populate competitors so EntryChecker never calls the live API.
        for full_name, first, last in [
            ("Baris Varol", "Baris", "Varol"),
            ("Denise Machin", "Denise", "Machin"),
        ]:
            self.comp.competitors[full_name] = _mock_dancer(self.comp_date, first, last)

        self.eligibility_results, self.level_violations = EntryChecker(self.comp).check()

    def test_tba_row_skipped_entirely(self):
        """The TBA row (missing follow name) shouldn't create a new competitor
        or an entry - only the two pre-populated dancers should exist."""
        self.assertEqual(set(self.comp.competitors.keys()), {"Baris Varol", "Denise Machin"})

    def test_eligible_entries_registered(self):
        """Bronze/Silver/Gold Smooth Waltz are all eligible (proficiency only
        sets a floor, not a ceiling) and should be registered as entries."""
        self.assertEqual(len(self.comp.entries), 3)

    def test_newcomer_violation_reported_and_not_registered(self):
        """Newcomer Tango is ineligible - these dancers aren't newcomers -
        and should show up as a violation, not an entry."""
        newcomer_results = [r for r in self.eligibility_results if not r.eligible]
        self.assertEqual(len(newcomer_results), 1)
        self.assertEqual(newcomer_results[0].violation_type.value, "newcomer")
        self.assertIn("Newcomer Am. Tango", newcomer_results[0].detail_message)

    def test_consecutive_level_violation_detected(self):
        """Registering for 3 distinct Smooth levels (Bronze/Silver/Gold) with
        consecutive_level_limit=2 should flag both dancers for too_many_levels."""
        too_many = [v for v in self.level_violations if v.violation_type == "too_many_levels"]
        self.assertEqual(len(too_many), 2)  # one per dancer (lead and follow)
        self.assertEqual({v.dancer_name for v in too_many}, {"Baris Varol", "Denise Machin"})
        for violation in too_many:
            self.assertEqual(violation.style, "Smooth")
            self.assertEqual(violation.levels, [1, 2, 3])  # Bronze, Silver, Gold indices


class TestRookieVetProcessedLast(unittest.TestCase):
    """Confirms check() registers Rookie/Vet rows after every other row,
    regardless of their order in the source data."""

    def test_rookie_lead_row_before_conflicting_regular_row(self):
        """A Rookie-Lead row listed BEFORE its conflicting same-partner
        regular-level row in the CSV should still be flagged - Rookie/Vet
        rows are processed last, not in file order."""
        comp_date = datetime.date(2026, 6, 1)
        raw_data = pd.DataFrame(
            {
                "Style": ["Smooth", "Smooth"],
                "Dance": ["Waltz", "Waltz"],
                "Skill": ["Rookie Lead", "Bronze"],  # Rookie-Lead row listed first
                "Lead First": ["Baris", "Baris"],
                "Lead Last": ["Varol", "Varol"],
                "Follow First": ["Denise", "Denise"],
                "Follow Last": ["Machin", "Machin"],
            }
        )
        comp = competition.Competition(
            comp_name="test",
            comp_date=comp_date,
            rv_ruleset="newcomer",
            consecutive_level_limit=2,
            rookie_max_level="Bronze",
            raw_data=raw_data,
        )
        # Baris is a brand-new (time-based newcomer) lead; Denise is
        # experienced, per _mock_dancer.
        lead_record = DancerRecord(
            cda_id=None,
            first="Baris",
            last="Varol",
            first_comp_date=None,
            created_date="2026-01-01",
            syllabus_pts=np.zeros((4, 19), dtype=int),
            open_pts=np.zeros((3, 4), dtype=int),
        )
        comp.competitors["Baris Varol"] = Dancer.from_data(comp_date, lead_record)
        comp.competitors["Denise Machin"] = _mock_dancer(comp_date, "Denise", "Machin")

        eligibility_results, _ = EntryChecker(comp).check()

        rookie_lead_results = [
            r for r in eligibility_results if r.violation_type == ViolationType.ROOKIE_LEAD
        ]
        self.assertEqual(len(rookie_lead_results), 1)
        self.assertIn(
            "is also registered for Smooth Waltz with the same partner",
            rookie_lead_results[0].detail_message,
        )


class TestCheckEntryAndRegisterEntry(unittest.TestCase):
    """Tests the single-entry building blocks check() is written in terms of."""

    def setUp(self):
        self.comp_date = datetime.date(2026, 6, 1)
        raw_data = pd.DataFrame(
            columns=[
                "Style",
                "Dance",
                "Skill",
                "Lead First",
                "Lead Last",
                "Follow First",
                "Follow Last",
            ]
        )
        self.comp = competition.Competition(
            comp_name="test",
            comp_date=self.comp_date,
            rv_ruleset="newcomer",
            consecutive_level_limit=2,
            rookie_max_level="Bronze",
            raw_data=raw_data,
        )
        self.lead = _mock_dancer(self.comp_date, "Baris", "Varol")
        self.follow = _mock_dancer(self.comp_date, "Denise", "Machin")
        self.comp.competitors["Baris Varol"] = self.lead
        self.comp.competitors["Denise Machin"] = self.follow
        self.partnership = Partnership(self.lead, self.follow)
        self.checker = EntryChecker(self.comp)

    def test_check_entry_does_not_register(self):
        """check_entry() should report eligibility without mutating any state -
        no entry created, no dancer/partnership entries touched."""
        dance_obj = Dance("Bronze", "Smooth", "Waltz")
        result = self.checker.check_entry(self.partnership, dance_obj)

        self.assertTrue(result.eligible)
        self.assertEqual(len(self.comp.entries), 0)
        self.assertEqual(len(self.lead.entries), 0)
        self.assertEqual(len(self.partnership.entries), 0)

    def test_check_entry_ineligible_does_not_register(self):
        """A dry-run check of an ineligible entry reports the violation but
        still doesn't touch any state."""
        dance_obj = Dance("Newcomer", "Smooth", "Tango")
        result = self.checker.check_entry(self.partnership, dance_obj)

        self.assertFalse(result.eligible)
        self.assertEqual(len(self.comp.entries), 0)

    def test_register_entry_eligible_commits(self):
        """register_entry() on an eligible dance creates the entry and
        returns no new level violations (only one level registered so far)."""
        dance_obj = Dance("Bronze", "Smooth", "Waltz")
        result, new_violations = self.checker.register_entry(self.partnership, dance_obj)

        self.assertTrue(result.eligible)
        self.assertEqual(new_violations, [])
        self.assertEqual(len(self.comp.entries), 1)
        self.assertIn(dance_obj, self.lead.entries)

    def test_register_entry_ineligible_does_not_commit(self):
        """register_entry() on an ineligible dance reports the violation but
        registers nothing."""
        dance_obj = Dance("Newcomer", "Smooth", "Tango")
        result, new_violations = self.checker.register_entry(self.partnership, dance_obj)

        self.assertFalse(result.eligible)
        self.assertEqual(new_violations, [])
        self.assertEqual(len(self.comp.entries), 0)

    def test_register_entry_duplicate_not_committed(self):
        """Registering the same dance/level twice should flag the second
        attempt as a duplicate and not add a second entry."""
        dance_obj = Dance("Bronze", "Smooth", "Waltz")
        first_result, _ = self.checker.register_entry(self.partnership, dance_obj)
        second_result, second_violations = self.checker.register_entry(self.partnership, dance_obj)

        self.assertTrue(first_result.eligible)
        self.assertFalse(second_result.eligible)
        self.assertEqual(second_result.violation_type.value, "duplicate_entry")
        self.assertEqual(second_violations, [])
        self.assertEqual(len(self.comp.entries), 1)

    def test_register_entry_nightclub_consecutive_level_not_committed(self):
        """Registering both levels of the same Nightclub dance should block
        the second registration entirely - not just exclude it from the
        dancer's own entries while still counting it elsewhere. Int/Adv is
        registered first since it's always eligible regardless of nc_beginner
        status, so this only exercises the new consecutive-level check."""
        first_result, _ = self.checker.register_entry(
            self.partnership, Dance("Intermediate/Advanced", "Nightclub", "Salsa")
        )
        second_result, second_violations = self.checker.register_entry(
            self.partnership, Dance("Beginner", "Nightclub", "Salsa")
        )

        self.assertTrue(first_result.eligible)
        self.assertFalse(second_result.eligible)
        self.assertEqual(second_result.violation_type.value, "nightclub_consecutive_level")
        self.assertEqual(second_violations, [])
        self.assertEqual(len(self.comp.entries), 1)
        self.assertEqual(len(self.lead.entries), 1)

    def test_register_entry_reports_level_violation_once(self):
        """A consecutive-level violation should be reported as a new_violation
        only on the entry that first triggers it - not again on a later entry
        that still satisfies the same violation."""
        _, first = self.checker.register_entry(self.partnership, Dance("Bronze", "Smooth", "Waltz"))
        _, second = self.checker.register_entry(
            self.partnership, Dance("Silver", "Smooth", "Waltz")
        )
        _, third = self.checker.register_entry(self.partnership, Dance("Gold", "Smooth", "Waltz"))
        _, fourth = self.checker.register_entry(self.partnership, Dance("Gold", "Smooth", "Tango"))

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        # Third entry pushes the lead+follow to 3 distinct Smooth levels,
        # exceeding consecutive_level_limit=2 for the first time.
        self.assertEqual(len(third), 2)
        self.assertEqual({v.dancer_name for v in third}, {"Baris Varol", "Denise Machin"})
        for violation in third:
            self.assertEqual(violation.violation_type, "too_many_levels")
        # Fourth entry is still Gold Smooth (a different dance, same level
        # set) - the violation already surfaced, so nothing new is reported.
        self.assertEqual(fourth, [])

    def test_register_entry_reports_violation_separately_per_dance(self):
        """Two different dances hitting the identical too_many_levels shape
        (same style, same levels) should each be reported - the dedup key
        has to include the dance, not just style/type/levels."""
        for level in ("Bronze", "Silver", "Gold"):
            _, waltz_violations = self.checker.register_entry(
                self.partnership, Dance(level, "Smooth", "Waltz")
            )
        self.assertEqual(len(waltz_violations), 2)
        for violation in waltz_violations:
            self.assertEqual(violation.dance, "Waltz")

        for level in ("Bronze", "Silver", "Gold"):
            _, tango_violations = self.checker.register_entry(
                self.partnership, Dance(level, "Smooth", "Tango")
            )
        self.assertEqual(len(tango_violations), 2)
        for violation in tango_violations:
            self.assertEqual(violation.dance, "Tango")


class TestReport(unittest.TestCase):
    """Tests for entry_checker._report()'s grouping/ordering."""

    def _run_report(self, eligibility_results, level_violations):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _report(eligibility_results, level_violations)
        return buf.getvalue()

    def test_split_level_notes_print_before_violations(self):
        """Split-level exceptions aren't violations, so they print as their
        own block up front, ahead of every grouped violation."""
        eligibility_results = [
            EligibilityResult(
                eligible=False,
                detail_message="ZZZ VIOLATION",
                subject_name="Zed Zed",
            ),
            EligibilityResult(
                eligible=True,
                is_split_level=True,
                split_level_info="SPLIT-LEVEL NOTE",
            ),
        ]
        output = self._run_report(eligibility_results, [])
        self.assertLess(output.index("SPLIT-LEVEL NOTE"), output.index("ZZZ VIOLATION"))

    def test_violations_grouped_by_subject_and_sorted(self):
        """A couple-level violation and an individual dancer's level
        violation should each file under the right subject, in sorted
        order - so an individual's own issues print adjacent to a couple
        violation they're part of, without duplicating either message."""
        eligibility_results = [
            EligibilityResult(
                eligible=False,
                detail_message="NEWCOMER VIOLATION: couple message",
                subject_name="Baris Varol & Denise Machin",
            ),
        ]
        level_violations = [
            LevelViolation(
                dancer_name="Baris Varol",
                style="Smooth",
                violation_type="too_many_levels",
                detail_message="LEVEL VIOLATION: Baris individual message",
            ),
            LevelViolation(
                dancer_name="Adam Aardvark",
                style="Smooth",
                violation_type="too_many_levels",
                detail_message="LEVEL VIOLATION: Adam individual message",
            ),
        ]
        output = self._run_report(eligibility_results, level_violations)
        adam_idx = output.index("Adam individual message")
        baris_idx = output.index("Baris individual message")
        couple_idx = output.index("couple message")
        self.assertLess(adam_idx, baris_idx)
        self.assertLess(baris_idx, couple_idx)

    def test_eligible_non_split_result_not_printed(self):
        eligibility_results = [EligibilityResult(eligible=True)]
        self.assertEqual(self._run_report(eligibility_results, []), "")

    def test_group_printed_under_subject_name_header(self):
        """Each group prints under a header naming its subject, immediately
        above that subject's own messages - the same per-person/couple
        headers the web UI's results page and .txt download use."""
        level_violations = [
            LevelViolation(
                dancer_name="Baris Varol",
                style="Smooth",
                violation_type="too_many_levels",
                detail_message="LEVEL VIOLATION: Baris individual message",
            ),
        ]
        output = self._run_report([], level_violations)
        header_idx = output.index("Baris Varol")
        message_idx = output.index("Baris individual message")
        self.assertLess(header_idx, message_idx)


if __name__ == "__main__":
    unittest.main()
