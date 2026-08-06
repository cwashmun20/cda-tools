"""Chronological point-update orchestration for points_updating.

Provides UpdateEngine, which processes one competition's results at a time
against a running ledger of Dancers, and run_backfill, which repeats that
per-competition update across every competition needed to catch the CDA
points database up to the present. Each competition's results are scored
against the ledger's state as of immediately before that competition -
never against points earned earlier in the same competition - so Split-
Level detection stays correct regardless of the order results happen to be
processed in.
"""

from datetime import date
from typing import Callable

from cda_core.lib.api.client import DancerRecord, lookup_dancer
from cda_core.lib.models.dancer import Dancer
from points_updating.lib.models.result import CompetitionResult, DancerRef
from points_updating.lib.points_calculator import PointsCalculator, ResultAward
from points_updating.lib.rules.eligibility_filter import filter_points_eligible
from points_updating.lib.rules.event_selection import select_points_event_results


class UpdateEngine:
    """Scores competitions against a running ledger of Dancers, one
    competition at a time.
    """

    def __init__(self, lookup: Callable[[str, str], DancerRecord] = lookup_dancer):
        """Create an UpdateEngine.

        Args:
            lookup: Fetches a DancerRecord for a first/last name, called the
                first time a dancer appears in the ledger. Defaults to the
                real CDA API; tests inject a fake instead.
        """
        self._lookup = lookup
        self._ledger: dict[str, Dancer] = {}

    def _get_or_create(self, ref: DancerRef, comp_date: date) -> Dancer:
        """Returns the ledgered Dancer for ref, fetching and ledgering one
        via self._lookup on its first appearance.
        """
        dancer = self._ledger.get(ref.full_name)
        if dancer is None:
            dancer = Dancer.from_data(comp_date, self._lookup(ref.first, ref.last))
            self._ledger[ref.full_name] = dancer
        else:
            dancer.curr_comp_date = comp_date
        return dancer

    def process_competition(self, results: list[CompetitionResult]) -> list[ResultAward]:
        """Scores one competition's results and applies the resulting
        point deltas to the ledger.

        Every result is scored against the ledger's state as of before this
        competition; only afterward are any deltas applied, so no result at
        this competition can affect how another result at the same
        competition is scored.

        Args:
            results: Every CompetitionResult from one competition.
        Returns:
            A ResultAward for each result that survived filtering and
            event selection (in the same order), i.e., every result that
            was actually scored.
        """
        results = filter_points_eligible(results)
        results = select_points_event_results(results)
        if not results:
            return []

        comp_date = results[0].competition_date
        dancers = {
            ref: self._get_or_create(ref, comp_date)
            for result in results
            for ref in (result.lead, result.follow)
        }

        awards = [
            PointsCalculator.compute(result, dancers[result.lead], dancers[result.follow])
            for result in results
        ]
        for result, award in zip(results, awards):
            dancers[result.lead].points.add(award.delta.syllabus, award.delta.open)
            dancers[result.follow].points.add(award.delta.syllabus, award.delta.open)

        return awards

    def run_backfill(self, competitions: list[list[CompetitionResult]]) -> list[list[ResultAward]]:
        """Processes every competition in chronological order, each
        building on the ledger state left by the last.

        Args:
            competitions: Each competition's results - order doesn't
                matter, this sorts by competition_date before processing.
        Returns:
            One list of ResultAwards per competition, in chronological
            order.
        Raises:
            ValueError: if any competition is empty - there's no
                competition_date to sort it by.
        """
        comps_chronological = sorted(competitions, key=_competition_date)
        return [self.process_competition(results) for results in comps_chronological]

    def final_totals(self) -> dict[str, Dancer]:
        """Every dancer touched so far, keyed by full name, with .points
        already holding their absolute new total (starting balance plus
        every delta applied) - the value a future write step would send
        per dancer, not a delta to combine with anything else at write
        time.
        """
        return dict(self._ledger)


def _competition_date(results: list[CompetitionResult]) -> date:
    """Sort key for run_backfill.

    Raises:
        ValueError: if results is empty - there's no competition_date to
            sort it by.
    """
    if not results:
        raise ValueError("Cannot sort an empty competition - it has no competition_date.")
    return results[0].competition_date
