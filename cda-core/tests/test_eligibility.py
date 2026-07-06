"""Tests for cda_core.lib.rules.eligibility module."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

import unittest
import datetime
import numpy as np
from api.client import DancerRecord
from models.dancer import Dancer
from models.dance import Dance
from models.partnership import Partnership
from rules.eligibility import EligibilityChecker
from rules.violations import ViolationType


class _MockDancer:
    """Minimal mock Dancer for testing without API access."""
    def __init__(self, name, is_newcomer=False, nc_beginner=False,
                 is_reg_newcomer=False, is_reg_bronze=False,
                 has_vet=False, has_rookie=False):
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

    def proficiency_level(self, dance_obj):
        return 1  # Default to Bronze level

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
        dance = Dance("IntAdv", "Nightclub", "Salsa")
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
        dance = Dance("RkLead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_lead_newcomer_ruleset_ineligible(self):
        lead = _MockDancer("Lead", is_newcomer=True)
        follow = _MockDancer("Follow", is_reg_newcomer=True, is_reg_bronze=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkLead", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_LEAD)

    def test_rookie_lead_level_ruleset_eligible(self):
        lead = _MockDancer("Lead", has_vet=False)
        follow = _MockDancer("Follow", has_rookie=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkLead", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_lead_level_ruleset_ineligible(self):
        lead = _MockDancer("Lead", has_vet=True)
        follow = _MockDancer("Follow", has_rookie=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkLead", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_LEAD)

    def test_rookie_follow_newcomer_ruleset_eligible(self):
        lead = _MockDancer("Lead", is_reg_newcomer=False, is_reg_bronze=False)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkFollow", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_follow_newcomer_ruleset_ineligible(self):
        lead = _MockDancer("Lead", is_reg_newcomer=True)
        follow = _MockDancer("Follow", is_newcomer=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkFollow", "Smooth", "Waltz")
        result = self.checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_FOLLOW)

    def test_rookie_follow_level_ruleset_eligible(self):
        lead = _MockDancer("Lead", has_rookie=False)
        follow = _MockDancer("Follow", has_vet=False)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkFollow", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertTrue(result.eligible)

    def test_rookie_follow_level_ruleset_ineligible(self):
        lead = _MockDancer("Lead", has_rookie=True)
        follow = _MockDancer("Follow", has_vet=True)
        partnership = _MockPartnership(lead, follow)
        dance = Dance("RkFollow", "Smooth", "Waltz")
        result = self.level_checker.check(partnership, dance)
        self.assertFalse(result.eligible)
        self.assertEqual(result.violation_type, ViolationType.ROOKIE_FOLLOW)


if __name__ == '__main__':
    unittest.main()