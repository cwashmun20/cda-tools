"""Tests for entry_checking.lib.rules.eligibility_checker module."""

import unittest
import datetime
import numpy as np
from entry_checking.lib.rules.eligibility_checker import EligibilityChecker
from entry_checking.lib.rules.violations import ViolationType
from utils.lib.api.client import DancerRecord
from utils.lib.models.dancer import Dancer
from utils.lib.models.dance import Dance
from utils.lib.models.entry import Entry
from utils.lib.models.partnership import Partnership


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
        points=0,
        above_own_cap=False,
        same_partner_entry=False,
    ):
        self.name = name
        self._is_newcomer = is_newcomer
        self._nc_beginner = nc_beginner
        self._is_reg_newcomer = is_reg_newcomer
        self._is_reg_bronze = is_reg_bronze
        self._has_vet = has_vet
        self._has_rookie = has_rookie
        self._points = points
        self._above_own_cap = above_own_cap
        self._same_partner_entry = same_partner_entry
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

    def get_points(self, dance_obj):
        return self._points

    def has_entry_above(self, style, dance, level_idx):
        return self._above_own_cap

    def has_entry_with_partnership(self, style, dance, partnership_obj):
        return self._same_partner_entry

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


def _make_new_dancer(name_first, name_last, syllabus_pts=None, open_pts=None):
    """Helper to create a real, time-based-newcomer Dancer with controlled
    points, for exercising the Rookie-Lead/Follow "pointed out of Newcomer"
    and own-entry-cap checks (which need a dancer who is_newcomer() but may
    still have points)."""
    if syllabus_pts is None:
        syllabus_pts = np.zeros((4, 19), dtype=int)
    if open_pts is None:
        open_pts = np.zeros((3, 4), dtype=int)
    record = DancerRecord(
        cda_id=None,
        first=name_first,
        last=name_last,
        first_comp_date=None,
        created_date="2026-01-01",
        syllabus_pts=syllabus_pts,
        open_pts=open_pts,
    )
    return Dancer.from_data(datetime.date(2026, 6, 1), record)


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

    def test_rookie_lead_newcomer_ruleset_message_names_the_failing_vet_condition(self):
        """The violation message should explain, in plain language, which
        vet-partner condition failed - and only that one, not a condition
        that didn't actually fail."""
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_reg_newcomer=True, is_reg_bronze=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Follow (Follow) is already registered for a Newcomer Smooth event, "
            "so can't act as the vet partner.",
            result.detail_message,
        )
        self.assertNotIn("Bronze", result.detail_message)
        self.assertNotIn("is not a newcomer", result.detail_message)

    def test_rookie_lead_newcomer_ruleset_message_names_lead_not_newcomer(self):
        lead = _MockDancer("Lead", is_newcomer=False)
        follow = _MockDancer("Follow", is_reg_newcomer=False, is_reg_bronze=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead) is not a newcomer, so is ineligible for the Rookie " "Lead designation.",
            result.detail_message,
        )

    def test_rookie_lead_newcomer_ruleset_pointed_out_of_newcomer(self):
        """A time-based newcomer who has already pointed out of Newcomer for
        this specific dance shouldn't qualify as Rookie for it."""
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = 7  # Newcomer Smooth Waltz pointed out
        lead = _make_new_dancer("Lead", "Dancer", syllabus)
        follow = _make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead Dancer) has pointed out of Newcomer Smooth Waltz, so "
            "is ineligible for the Rookie Lead designation.",
            result.detail_message,
        )

    def test_rookie_lead_newcomer_ruleset_above_own_cap_default_bronze(self):
        """Under the default Bronze cap, a Rookie who also has a Silver
        entry for this same dance in this style (with a different partner)
        shouldn't qualify as Rookie for it."""
        lead = _make_new_dancer("Lead", "Dancer")
        other_partner = _make_new_dancer("Other", "Partner")
        Entry(Dance("Silver", "Smooth", "Waltz"), Partnership(lead, other_partner))

        follow = _make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead Dancer) is registered above Bronze in Smooth Waltz, "
            "exceeding the level a Rookie may also compete at.",
            result.detail_message,
        )

    def test_rookie_lead_newcomer_ruleset_silver_cap_allows_silver_entry(self):
        """With rookie_max_level='Silver', a Rookie who also has a Silver
        entry for this same dance should still qualify - only Gold+ should
        disqualify under that cap."""
        checker = EligibilityChecker("newcomer", rookie_max_level="Silver")
        lead = _make_new_dancer("Lead", "Dancer")
        other_partner = _make_new_dancer("Other", "Partner")
        Entry(Dance("Silver", "Smooth", "Waltz"), Partnership(lead, other_partner))

        follow = _make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_lead_newcomer_ruleset_silver_cap_disqualifies_gold_entry(self):
        checker = EligibilityChecker("newcomer", rookie_max_level="Silver")
        lead = _make_new_dancer("Lead", "Dancer")
        other_partner = _make_new_dancer("Other", "Partner")
        Entry(Dance("Gold", "Smooth", "Waltz"), Partnership(lead, other_partner))

        follow = _make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead Dancer) is registered above Silver in Smooth Waltz, "
            "exceeding the level a Rookie may also compete at.",
            result.detail_message,
        )

    def test_rookie_lead_newcomer_ruleset_same_partner_regular_entry(self):
        """A Rookie who has a regular-level entry for this same dance WITH
        THE SAME partner as this Rookie/Vet entry should be disqualified."""
        lead = _make_new_dancer("Lead", "Dancer")
        follow = _make_new_dancer("Follow", "Dancer")
        partnership = Partnership(lead, follow)
        Entry(Dance("Bronze", "Smooth", "Waltz"), partnership)

        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead Dancer) is also registered for Smooth Waltz with "
            "the same partner (Follow Dancer) outside the Rookie Lead "
            "designation.",
            result.detail_message,
        )

    def test_invalid_rookie_max_level_raises_error(self):
        with self.assertRaises(ValueError):
            EligibilityChecker("newcomer", rookie_max_level="Gold")

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

    def test_rookie_lead_level_ruleset_message_names_failing_conditions(self):
        lead = _MockDancer("Lead", has_vet=True)
        follow = _MockDancer("Follow", has_rookie=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("Rookie Lead", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Lead (Lead) already has Silver-or-above Smooth entries, so is "
            "ineligible for the Rookie Lead designation.",
            result.detail_message,
        )
        self.assertIn(
            "Follow (Follow) already has Bronze-or-below Smooth entries, "
            "so can't act as the vet partner.",
            result.detail_message,
        )

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

    def test_rookie_follow_newcomer_ruleset_pointed_out_of_newcomer(self):
        syllabus = np.zeros((4, 19), dtype=int)
        syllabus[0][5] = 7  # Newcomer Smooth Waltz pointed out
        follow = _make_new_dancer("Follow", "Dancer", syllabus)
        lead = _make_new_dancer("Lead", "Dancer")
        partnership = Partnership(lead, follow)
        dance = Dance("Rookie Follow", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertIn(
            "Follow (Follow Dancer) has pointed out of Newcomer Smooth "
            "Waltz, so is ineligible for the Rookie Follow designation.",
            result.detail_message,
        )

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
