"""Shared points-update logic for the web UI's route handler.

routes.py calls run_update() so the parse -> UpdateEngine -> report
sequence exists in exactly one place, mirroring
entry_checking/lib/webapp/check_service.py's run_check().
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.parsing.routing import parse_results_url
from points_updating.lib.report import UpdateReport, build_report, render_report
from points_updating.lib.update_engine import UpdateEngine
from utils.lib.api.client import DancerRecord, lookup_dancer

_CACHE_DIR = Path("data/cache")
_MIN_DELAY_SECONDS = 1.0


@dataclass
class UpdateError:
    """A user-facing error from run_update(), with an HTTP status to report it under."""

    message: str
    status_code: int = 400


@dataclass
class UpdateSuccess:
    """The result of a successful points update.

    Text is pre-rendered here rather than left to the template, so the
    "all dancers" view and each individual dancer's view are both plain
    strings the page can display and download exactly as-is.
    """

    dancer_names: list[str]  # sorted by last name
    all_text: str
    dancer_text: dict[str, str]


def run_update(
    urls: list[str],
    date_strs: list[str],
    lookup: Callable[[str, str], DancerRecord] = lookup_dancer,
) -> UpdateSuccess | UpdateError:
    """Runs a full points update from raw form input.

    Args:
        urls: One results-page URL per competition.
        date_strs: Each competition's date, as an ISO "YYYY-MM-DD" string,
            paired by position with urls.
        lookup: Fetches a DancerRecord for a first/last name - forwarded to
            UpdateEngine; tests inject a fake so no real API call happens.
    Returns:
        An UpdateSuccess with the rendered report(s) to display, or an
        UpdateError describing what went wrong and what HTTP status to
        report it under.
    """
    if not urls:
        return UpdateError("At least one results link is required.")

    parsed_dates = []
    for date_str in date_strs:
        try:
            parsed_dates.append(date.fromisoformat(date_str))
        except ValueError:
            return UpdateError(f"'{date_str}' is not a valid date (expected YYYY-MM-DD).")

    client = ThrottledClient(min_delay_seconds=_MIN_DELAY_SECONDS, cache_dir=_CACHE_DIR)
    competitions = []
    for url, comp_date in zip(urls, parsed_dates):
        try:
            competitions.append(parse_results_url(url, comp_date, client))
        except Exception as e:
            # Deliberately broad: fetching/parsing a live third-party page
            # can fail in many ways (network errors, unrecognized host,
            # unsupported event shapes) - all become one clean message
            # rather than a 500 page.
            return UpdateError(f"Failed to fetch/parse {url!r}: {e}", 502)

    engine = UpdateEngine(lookup=lookup)
    awards_per_competition = engine.run_backfill(competitions)
    all_awards = [award for comp_awards in awards_per_competition for award in comp_awards]
    starting_totals = engine.starting_totals()
    final_totals = {name: dancer.points for name, dancer in engine.final_totals().items()}
    report = build_report(all_awards, starting_totals, final_totals)

    dancer_names = sorted((d.dancer_name for d in report.dancer_reports), key=_last_name_key)
    dancer_text = {
        d.dancer_name: render_report(UpdateReport(dancer_reports=[d]))
        for d in report.dancer_reports
    }
    return UpdateSuccess(
        dancer_names=dancer_names, all_text=render_report(report), dancer_text=dancer_text
    )


def _last_name_key(full_name: str) -> str:
    return full_name.strip().rpartition(" ")[2] or full_name
