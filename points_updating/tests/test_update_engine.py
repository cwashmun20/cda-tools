"""Tests for points_updating.lib.update_engine module."""

import unittest
from datetime import date

import numpy as np

from cda_core.lib.api.client import DancerRecord
from cda_core.lib.models.dance import Dance
from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.rules import cascade
from points_updating.lib.update_engine import UpdateEngine


def _make_record(first, last, syllabus_pts=None, open_pts=None) -> DancerRecord:
    """A pre-existing (cda_id set), experienced (>1 year) dancer record."""
    if syllabus_pts is None:
        syllabus_pts = np.zeros((4, 19), dtype=int)
    if open_pts is None:
        open_pts = np.zeros((3, 4), dtype=int)
    return DancerRecord(
        cda_id=1,
        first=first,
        last=last,
        first_comp_date=date(2020, 1, 1),
        created_date="2020-01-01",
        syllabus_pts=syllabus_pts,
        open_pts=open_pts,
    )


def _make_lookup(records: dict):
    """Fake dancer lookup - returns a pre-built record for known (first,
    last) keys, or an empty/not-found record (mirroring the real API's
    not-found behavior) for anyone else.
    """

    def lookup(first: str, last: str) -> DancerRecord:
        if (first, last) in records:
            return records[(first, last)]
        return DancerRecord(
            cda_id=None,
            first=first,
            last=last,
            first_comp_date=None,
            created_date="2026-01-01",
            syllabus_pts=np.zeros((4, 19), dtype=int),
            open_pts=np.zeros((3, 4), dtype=int),
        )

    return lookup


def _make_result(
    dance: Dance, lead: DancerRef, follow: DancerRef, place: int, num_rounds: int, comp_date: date
) -> CompetitionResult:
    return CompetitionResult(
        dance=dance,
        lead=lead,
        follow=follow,
        place=place,
        num_rounds=num_rounds,
        competition_name="Test Classic",
        competition_date=comp_date,
        event_dances=(dance,),
    )


class TestUpdateEngine(unittest.TestCase):
    """Tests for UpdateEngine."""

    def test_scores_every_result_against_pre_competition_state(self):
        """A naive, sequentially-applied implementation would let an
        earlier result in this competition change a later result's
        Split-Level determination. Lead starts one point-out short of
        pointing out of Bronze Smooth Waltz (4/7); follow is already
        pointed out through Silver (proficiency Gold). The first result
        pushes lead's Bronze Smooth Waltz to exactly 7, which - if applied
        before the second result is scored - would raise lead's proficiency
        enough to shrink the lead/follow gap under 2 and disqualify the
        second result from the Split-Level Exception it should still
        qualify for.
        """
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        lead_syllabus = np.zeros((4, 19), dtype=int)
        lead_syllabus[0][5] = 7  # Newcomer Smooth Waltz - already pointed out
        lead_syllabus[1][5] = 4  # Bronze Smooth Waltz - one placement short
        follow_syllabus = np.zeros((4, 19), dtype=int)
        follow_syllabus[0][5] = follow_syllabus[1][5] = follow_syllabus[2][5] = 7  # -> Gold (3)
        records = {
            ("Lead", "Dancer"): _make_record("Lead", "Dancer", lead_syllabus),
            ("Follow", "Dancer"): _make_record("Follow", "Dancer", follow_syllabus),
        }
        comp_date = date(2025, 10, 4)
        dance1 = Dance("Bronze", "Smooth", "Waltz")
        result1 = _make_result(dance1, lead, follow, place=1, num_rounds=3, comp_date=comp_date)
        dance2 = Dance("Silver", "Smooth", "Waltz")
        result2 = _make_result(dance2, lead, follow, place=1, num_rounds=2, comp_date=comp_date)

        engine = UpdateEngine(lookup=_make_lookup(records))
        awards = engine.process_competition([result1, result2])

        self.assertFalse(awards[0].is_split_level)
        self.assertTrue(awards[1].is_split_level)
        expected_delta2 = cascade.build_cascade_delta(dance2, (9, 18, 21))  # 3x (3, 6, 7)
        self.assertTrue(np.array_equal(awards[1].delta.syllabus, expected_delta2.syllabus))
        self.assertTrue(np.array_equal(awards[1].delta.open, expected_delta2.open))

    def test_run_backfill_carries_points_across_competitions(self):
        """A second competition's scoring builds on the ledger state a
        first competition's processing already applied."""
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        comp1 = [
            _make_result(dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4))
        ]
        comp2 = [
            _make_result(dance, lead, follow, place=2, num_rounds=3, comp_date=date(2025, 11, 15))
        ]

        engine = UpdateEngine(lookup=_make_lookup({}))
        engine.run_backfill([comp1, comp2])

        totals = engine.final_totals()
        # comp1 1st (3, 6, 7) + comp2 2nd (2, 4, 7) at Bronze/Newcomer Smooth Waltz.
        for name in ("Lead Dancer", "Follow Dancer"):
            self.assertEqual(totals[name].points.syllabus_data[1][5], 5)  # danced: 3 + 2
            self.assertEqual(totals[name].points.syllabus_data[0][5], 10)  # one below: 6 + 4

    def test_run_backfill_sorts_competitions_before_processing(self):
        """run_backfill must sort by competition_date itself, not trust the
        caller's order. Lead starts one point-out short of pointing out of
        Bronze Smooth Waltz; the earlier competition pushes them over that
        threshold. Passed in chronological order, the later competition's
        Silver result is scored using lead's post-Bronze-competition
        proficiency and correctly falls outside the Split-Level Exception.
        Passing the two competitions to run_backfill in reverse order
        should still produce that same, chronologically-correct result.
        """
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        lead_syllabus = np.zeros((4, 19), dtype=int)
        lead_syllabus[0][5] = 7  # Newcomer Smooth Waltz - already pointed out
        lead_syllabus[1][5] = 4  # Bronze Smooth Waltz - one placement short
        follow_syllabus = np.zeros((4, 19), dtype=int)
        follow_syllabus[0][5] = follow_syllabus[1][5] = follow_syllabus[2][5] = 7  # -> Gold (3)
        records = {
            ("Lead", "Dancer"): _make_record("Lead", "Dancer", lead_syllabus),
            ("Follow", "Dancer"): _make_record("Follow", "Dancer", follow_syllabus),
        }
        dance1 = Dance("Bronze", "Smooth", "Waltz")
        earlier = [
            _make_result(dance1, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4))
        ]
        dance2 = Dance("Silver", "Smooth", "Waltz")
        later = [
            _make_result(dance2, lead, follow, place=1, num_rounds=2, comp_date=date(2025, 11, 15))
        ]

        engine = UpdateEngine(lookup=_make_lookup(records))
        # Passed out of chronological order - run_backfill must sort them itself.
        awards = engine.run_backfill([later, earlier])

        self.assertFalse(awards[0][0].is_split_level)  # earlier (Bronze) result
        self.assertFalse(awards[1][0].is_split_level)  # later (Silver) result

    def test_run_backfill_raises_for_empty_competition(self):
        """An empty competition has no results to derive a competition_date
        from, so it can't be sorted - this must raise rather than silently
        guessing an ordering."""
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        non_empty = [
            _make_result(dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4))
        ]

        engine = UpdateEngine(lookup=_make_lookup({}))

        with self.assertRaises(ValueError):
            engine.run_backfill([[], non_empty])

    def test_new_dancer_starts_at_zero_and_existing_starting_balance_carries(self):
        """A brand-new dancer (not found by lookup) is ledgered starting
        from zero; an existing dancer's real starting balance is preserved
        underneath the delta this competition adds."""
        existing = DancerRef(first="Alice", last="Existing")
        new = DancerRef(first="Carol", last="New")
        existing_syllabus = np.zeros((4, 19), dtype=int)
        existing_syllabus[1][5] = 10  # pre-existing Bronze Smooth Waltz points
        records = {("Alice", "Existing"): _make_record("Alice", "Existing", existing_syllabus)}
        dance = Dance("Bronze", "Smooth", "Waltz")
        comp_date = date(2025, 10, 4)
        result = _make_result(dance, existing, new, place=1, num_rounds=3, comp_date=comp_date)

        engine = UpdateEngine(lookup=_make_lookup(records))
        engine.process_competition([result])

        totals = engine.final_totals()
        self.assertEqual(totals["Alice Existing"].points.syllabus_data[1][5], 13)  # 10 + 3
        self.assertEqual(totals["Carol New"].points.syllabus_data[1][5], 3)  # 0 + 3

    def test_lead_and_follow_have_independent_points_objects(self):
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Bronze", "Smooth", "Waltz")
        result = _make_result(
            dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4)
        )

        engine = UpdateEngine(lookup=_make_lookup({}))
        engine.process_competition([result])

        totals = engine.final_totals()
        self.assertIsNot(totals["Lead Dancer"].points, totals["Follow Dancer"].points)
        self.assertIsNot(
            totals["Lead Dancer"].points.syllabus_data, totals["Follow Dancer"].points.syllabus_data
        )

    def test_filtered_out_dancer_never_reaches_ledger(self):
        """A dancer who only appears in a non-points-eligible result (here,
        Nightclub) is filtered out before dancer resolution, so they're
        never even ledgered."""
        lead = DancerRef(first="Lead", last="Dancer")
        follow = DancerRef(first="Follow", last="Dancer")
        dance = Dance("Beginner", "Nightclub", "Salsa")
        result = _make_result(
            dance, lead, follow, place=1, num_rounds=3, comp_date=date(2025, 10, 4)
        )

        engine = UpdateEngine(lookup=_make_lookup({}))
        awards = engine.process_competition([result])

        self.assertEqual(awards, [])
        self.assertEqual(engine.final_totals(), {})


if __name__ == "__main__":
    unittest.main()
