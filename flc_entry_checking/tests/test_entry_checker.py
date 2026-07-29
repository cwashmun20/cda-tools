"""Integration tests for flc_entry_checking.lib.entry_checker.

Exercises the full Competition + EntryChecker pipeline together, rather than
each rules/parsing module in isolation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'cda_core', 'lib'))

import unittest
import datetime
import numpy as np
import pandas as pd

import competition
from api.client import DancerRecord
from models.dancer import Dancer
from entry_checker import EntryChecker


def _mock_dancer(comp_date, first, last):
    """Build an experienced (>1yr), zero-points Dancer without hitting the API."""
    record = DancerRecord(
        cda_id=1, first=first, last=last,
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
        raw_data = pd.DataFrame({
            "Style":       ["Smooth", "Smooth", "Smooth", "Smooth",  "Smooth"],
            "Dance":       ["Waltz",  "Waltz",  "Waltz",  "Tango",   "Waltz"],
            "Skill":       ["Bronze", "Silver", "Gold",   "Newcomer", "Bronze"],
            "Lead First":  ["Baris",   "Baris",   "Baris",   "Baris",    "Baris"],
            "Lead Last":   ["Varol",    "Varol",    "Varol",    "Varol",     "Varol"],
            "Follow First": ["Denise",  "Denise",   "Denise",   "Denise",    np.nan],  # last row is TBA
            "Follow Last": ["Machin",  "Machin",  "Machin",  "Machin",   np.nan],
        })
        self.comp = competition.Competition(
            comp_name="test",
            comp_date=self.comp_date,
            rv_ruleset="newcomer",
            flc_level_limit=2,
            raw_data=raw_data,
        )
        # Pre-populate competitors so EntryChecker never calls the live API.
        for full_name, first, last in [("Baris Varol", "Baris", "Varol"), ("Denise Machin", "Denise", "Machin")]:
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
        flc_level_limit=2 should flag both dancers for too_many_levels."""
        too_many = [v for v in self.level_violations if v.violation_type == "too_many_levels"]
        self.assertEqual(len(too_many), 2)  # one per dancer (lead and follow)
        self.assertEqual({v.dancer_name for v in too_many}, {"Baris Varol", "Denise Machin"})
        for violation in too_many:
            self.assertEqual(violation.style, "Smooth")
            self.assertEqual(violation.levels, [1, 2, 3])  # Bronze, Silver, Gold indices


if __name__ == '__main__':
    unittest.main()
