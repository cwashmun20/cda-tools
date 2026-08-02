"""Shared entry-checking logic for the web UI's HTML and JSON routes.

Both routes.py's HTML form handler and its JSON API handler call run_check()
so the parse -> Competition -> EntryChecker.check() -> error-normalization
sequence exists in exactly one place.
"""

from dataclasses import dataclass
from datetime import date
from typing import IO, Union

from cda_core.lib import competition
from cda_core.lib.api.client import DancerLookupError
from entry_checking.lib.entry_checker import EntryChecker
from entry_checking.lib.parsing.csv_reader import read_entries
from entry_checking.lib.parsing.multi_dance_expander import expand_multi_dance_events
from entry_checking.lib.report_view import ReportView, build_report_view


@dataclass
class CheckError:
    """A user-facing error from run_check(), with an HTTP status to report it under."""

    message: str
    status_code: int


@dataclass
class CheckSuccess:
    """The result of a successful entry check."""

    report_view: ReportView


def run_check(
    comp_name: str,
    comp_date_str: str,
    rv_ruleset: str,
    rookie_max_level: str,
    consecutive_level_limit_str: str,
    csv_source: Union[str, "IO[bytes]", "IO[str]"],
) -> CheckSuccess | CheckError:
    """Run a full entry check from raw form/request input.

    Args:
        comp_name: The competition's name.
        comp_date_str: The competition's date, as an ISO "YYYY-MM-DD" string.
        rv_ruleset: Either "newcomer" or "level".
        rookie_max_level: Either "Bronze" or "Silver" (unused under "level").
        consecutive_level_limit_str: The consecutive-level limit, as a string.
        csv_source: The uploaded entry spreadsheet - a path or a file-like
                    object (e.g. a Werkzeug FileStorage's .stream).
    Returns:
        A CheckSuccess with the report to display, or a CheckError describing
        what went wrong and what HTTP status to report it under.
    """
    try:
        raw_data = expand_multi_dance_events(read_entries(csv_source))
    except ValueError as e:
        return CheckError(str(e), 400)

    try:
        comp_date = date.fromisoformat(comp_date_str)
    except ValueError:
        return CheckError(f"'{comp_date_str}' is not a valid date (expected YYYY-MM-DD).", 400)

    try:
        consecutive_level_limit = int(consecutive_level_limit_str)
    except ValueError:
        return CheckError(
            f"'{consecutive_level_limit_str}' is not a valid consecutive-level limit.", 400
        )

    try:
        comp = competition.Competition(
            comp_name, comp_date, rv_ruleset, consecutive_level_limit, rookie_max_level, raw_data
        )
        eligibility_results, level_violations = EntryChecker(comp).check()
    except ValueError as e:
        # Covers an invalid rv_ruleset/rookie_max_level - unreachable via the
        # HTML form's constrained dropdowns, but reachable via /api/check.
        return CheckError(str(e), 400)
    except DancerLookupError as e:
        return CheckError(str(e), 502)

    return CheckSuccess(report_view=build_report_view(eligibility_results, level_violations))
