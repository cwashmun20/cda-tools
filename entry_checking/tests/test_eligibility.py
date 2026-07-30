"""Tests for entry_checking.lib.rules.eligibility module."""

import unittest
import datetime
import numpy as np
from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dancer import Dancer
from cda_core.lib.models.dance import Dance
from cda_core.lib.models.partnership import Partnership
from entry_checking.lib.rules.eligibility import EligibilityChecker
from entry_checking.lib.rules.violations import ViolationType


class _MockDancer:
    """Minimal mock Dancer for testing without API access."""

    def __init__(
        self,
        name,
        is_newcomer=False,
        nc_beginner=False,
        is_reg_newcomer=False,
        is_reg_bronze=False,
        has_vet=False,
        has_rookie=False,
    ):
        self.name = name
        self._is_newcomer = is_newcomer
        self._nc_beginner = nc_beginner
        self._is_reg_newcomer = is_reg_newcomer
        self._is_reg_bronze = is_reg_bronze
        self._has_vet = has_vet
        self._has_rookie = has_rookie
        self.entries = set()

    def is_newcomer(self):
        return self._is_newcomer

    def nc_beginner(self):
        return self._nc_beginner

    def is_registered_newcomer(self, style):
        return self._is_reg_newcomer

    def is_registered_bronze(self, style):
        return self._is_reg_bronze

    def has_vet_entries(self, style):
        return self._has_vet

    def has_rookie_entries(self, style):
        return self._has_rookie

    def __repr__(self):
        return self.name


class _MockPartnership:
    """Minimal mock Partnership for testing."""

    def __init__(self, lead, follow, newcomers=False, nc_beginners=False):
        self.lead = lead
        self.follow = follow
        self.names = lead.name + " & " + follow.name
        self.newcomers = newcomers
        self.nc_beginners = nc_beginners
        self.entries = set()


def _make_dancer(name_first, name_last, syllabus_pts=None, open_pts=None):
    """Helper to create a real Dancer with controlled points, for exercising
    the proficiency-check fallthrough in EligibilityChecker (Split-Level
    Exception / Pointed-Out violations), which now calls ProficiencyCalculator
    directly rather than a mockable Dancer method."""
    if syllabus_pts is None:
        syllabus_pts = np.zeros((4, 19), dtype=int)
    if open_pts is None:
        open_pts = np.zeros((3, 4), dtype=int)
    record = DancerRecord(
        cda_id=1,
        first=name_first,
        last=name_last,
        first_comp_date=datetime.date(2020, 1, 1),  # >1 year ago - not a newcomer
        created_date="2020-01-01",
        syllabus_pts=syllabus_pts,
        open_pts=open_pts,
    )
    return Dancer.from_data(datetime.date(2026, 1, 1), record)


class TestEligibilityChecker(unittest.TestCase):
    """Tests for the EligibilityChecker class."""

    def setUp(self):
        self.checker = EligibilityChecker("newcomer")
        self.level_checker = EligibilityChecker("level")

    def test_invalid_ruleset_raises_error(self):
        with self.assertRaises(ValueError):
            EligibilityChecker("invalid")

    def test_nightclub_intadv_always_eligible(self):
        lead = _MockDancer("Lead")
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Intermediate/Advanced", "Nightclub", "Salsa")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)
        self.assertIsNone(result.violation_type)

    def test_championship_always_eligible(self):
        lead = _MockDancer("Lead")
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Championship", "Standard", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_duplicate_entry_for_lead(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        lead = _MockDancer("Lead")
        lead.entries = {dance}
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.DUPLICATE_ENTRY)

    def test_duplicate_entry_for_follow(self):
        dance = Dance("Bronze", "Smooth", "Waltz")
        lead = _MockDancer("Lead")
        follow = _MockDancer("Follow")
        follow.entries = {dance}
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.DUPLICATE_ENTRY)

    def test_duplicate_entry_takes_priority_over_always_eligible(self):
        """Even Championship/NC Int-Adv, which are otherwise unconditionally
        eligible, should still be flagged as a duplicate."""
        dance = Dance("Championship", "Standard", "Waltz")
        lead = _MockDancer("Lead")
        lead.entries = {dance}
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.DUPLICATE_ENTRY)

    def test_nightclub_consecutive_level_violation(self):
        """Already registered Beginner Salsa - the otherwise-always-eligible
        Int/Adv Salsa should be blocked as a consecutive-level conflict."""
        lead = _MockDancer("Lead")
        lead.entries = {Dance("Beginner", "Nightclub", "Salsa")}
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(
            partnership, Dance("Intermediate/Advanced", "Nightclub", "Salsa")
        )
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.NIGHTCLUB_CONSECUTIVE_LEVEL)

    def test_nightclub_consecutive_level_violation_reverse_direction(self):
        beginner_dance = Dance("Beginner", "Nightclub", "Salsa")
        intadv_dance = Dance("Intermediate/Advanced", "Nightclub", "Salsa")
        lead = _MockDancer("Lead")
        follow = _MockDancer("Follow")
        follow.entries = {intadv_dance}
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(partnership, beginner_dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.NIGHTCLUB_CONSECUTIVE_LEVEL)

    def test_nightclub_consecutive_level_different_dance_not_flagged(self):
        lead = _MockDancer("Lead")
        lead.entries = {Dance("Beginner", "Nightclub", "Salsa")}
        follow = _MockDancer("Follow")
        partnership = _MockPartnership(lead, follow)
        result = self.checker.check(
            partnership, Dance("Intermediate/Advanced", "Nightclub", "Bachata")
        )
        self.assertTrue(result.eligible)

    def test_beginner_nightclub_both_nc_beginners(self):
        lead = _MockDancer("Lead", nc_beginner=True)
        follow = _MockDancer("Follow", nc_beginner=True)
        partnership = _MockPartnership(lead, follow, nc_beginners=True)
        dance = Dance("Beginner", "Nightclub", "Salsa")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_beginner_nightclub_not_nc_beginners(self):
        lead = _MockDancer("Lead", nc_beginner=False)
        follow = _MockDancer("Follow", nc_beginner=False)
        partnership = _MockPartnership(lead, follow, nc_beginners=False)
        dance = Dance("Beginner", "Nightclub", "Salsa")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.NIGHTCLUB_BEGINNER)

    def test_newcomer_both_newcomers(self):
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow, newcomers=True)
        dance = Dance("Newcomer", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_newcomer_not_both_newcomers(self):
        lead = _MockDancer("Lead", is_newcomer=False)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow, newcomers=False)
        dance = Dance("Newcomer", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.NEWCOMER)

    def test_rookie_lead_newcomer_ruleset_eligible(self):
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_reg_newcomer=False, is_reg_bronze=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_lead_newcomer_ruleset_ineligible(self):
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_reg_newcomer=True, is_reg_bronze=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_LEAD)

    def test_rookie_lead_newcomer_ruleset_ineligible_message_explains_why(self):
        """The violation message should state which of the vet-partner
        conditions failed, not just that the lead is (or isn't) a rookie."""
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_reg_newcomer=True, is_reg_bronze=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "is already registered for a Newcomer Smooth event: True", result.detail_message
        )
        self.assertIn(
            "is already registered for a Bronze Smooth event: False", result.detail_message
        )

    def test_rookie_lead_level_ruleset_eligible(self):
        lead = _MockDancer("Lead", has_vet=False)
        follow = _MockDancer("Follow", has_rookie=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_lead_level_ruleset_ineligible(self):
        lead = _MockDancer("Lead", has_vet=True)
        follow = _MockDancer("Follow", has_rookie=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_LEAD)

    def test_rookie_follow_newcomer_ruleset_eligible(self):
        lead = _MockDancer("Lead", is_reg_newcomer=False, is_reg_bronze=False)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Follow", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_follow_newcomer_ruleset_ineligible(self):
        lead = _MockDancer("Lead", is_reg_newcomer=True)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Follow", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_FOLLOW)

    def test_rookie_follow_level_ruleset_eligible(self):
        lead = _MockDancer("Lead", has_rookie=False)
        follow = _MockDancer("Follow", has_vet=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Follow", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_follow_level_ruleset_ineligible(self):
        lead = _MockDancer("Lead", has_rookie=True)
        follow = _MockDancer("Follow", has_vet=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Follow", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_FOLLOW)

    def test_split_level_exception(self):
        """Lead pointed out to Gold (3), follow at the Bronze floor (1): the
        gap is >=2 levels, and combined_level (max-1 = 2) equals the Silver
        event they're entering, so the split-level exception applies."""
        syllabus = np.zeros((4, 19), dtype=int)
        # Smooth Waltz (col 5): pointed out at Newcomer/Bronze/Silver, not Gold.
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = 7
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer")  # zero points -> floor of Bronze (1)
        partnership = Partnership(lead, follow)
        dance = Dance("Silver", "Smooth", "Waltz")

        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)
        self.assertTrue(result.is_split_level)
        self.assertIsNotNone(result.split_level_info)

    def test_split_level_exception_not_triggered_when_combined_mismatches_event(self):
        """Same >=2 level gap as above, but registered for a level where
        combined_level doesn't match the event - falls through to a normal
        eligibility check instead of the split-level exception."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = syllabus[2][5] = 7  # lead -> Gold (3)
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer")  # Bronze (1)
        partnership = Partnership(lead, follow)
        # combined_level = 3 - 1 = 2 (Silver); registering for Bronze (1) instead.
        dance = Dance("Bronze", "Smooth", "Waltz")

        result = self.checker.check(partnership, dance)
        self.assertFalse(result.is_split_level)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.POINTED_OUT)

    def test_pointed_out_violation(self):
        """Both partners pointed out to Silver (2) in Smooth Waltz; registering
        for Bronze (1) - below their proficiency - is a Pointed-Out violation."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = 7  # Newcomer/Bronze pointed out, not Silver
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer", syllabus.copy())
        partnership = Partnership(lead, follow)
        dance = Dance("Bronze", "Smooth", "Waltz")

        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.POINTED_OUT)
        self.assertIn("POINTED OUT VIOLATION", result.detail_message)

    def test_pointed_out_violation_includes_recommended_levels(self):
        """A pointed-out violation's detail message should include the
        partnership's recommended level(s) for the style, not just each
        dancer's individual lowest allowed level."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = 7  # Newcomer/Bronze pointed out, not Silver
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer", syllabus.copy())
        partnership = Partnership(lead, follow)
        dance = Dance("Bronze", "Smooth", "Waltz")

        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Recommended Smooth level(s) for this partnership: Silver and Gold",
            result.detail_message,
        )

    def test_pointed_out_eligible_at_or_above_proficiency(self):
        """A dancer may always register at or above their proficiency level -
        pointing out only raises the floor, it doesn't cap the ceiling."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = syllabus[1][5] = 7  # both pointed out to Silver (2)
        lead = _make_dancer("Lead", "Dancer", syllabus)
        follow = _make_dancer("Follow", "Dancer", syllabus.copy())
        partnership = Partnership(lead, follow)
        dance = Dance("Gold", "Smooth", "Waltz")  # above their floor - fine

        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)


if __name__ == "__main__":
    unittest.main()
