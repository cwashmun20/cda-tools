"""Integration tests for entry_checking.lib.entry_checker.

Exercises the full Competition + EntryChecker pipeline together, rather than
each rules/parsing module in isolation.
"""

import unittest
import datetime
import numpy as np
import pandas as pd

from cda_core.lib import competition
from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.dancer import Dancer
from cda_core.lib.models.partnership import Partnership
from entry_checking.lib.entry_checker import EntryChecker


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


if __name__ == "__main__":
    unittest.main()
