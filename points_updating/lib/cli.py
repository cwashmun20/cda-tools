"""Command-line entry point for points_updating: fetches and parses one or
more competitions' results, scores them, and writes a rendered
point-update report to disk.

Usage:
    python -m points_updating.lib.cli \\
        --result https://results.o2cm.com/event3.asp?event=isc25 2025-11-14 \\
        --result https://ballroomcompexpress.com/results.php?cid=178 2025-03-01

    (or via installed entry point: points-updater)
"""

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from points_updating.lib.parsing.http_client import ThrottledClient
from points_updating.lib.parsing.routing import parse_results_url
from points_updating.lib.report import build_report, render_report
from points_updating.lib.update_engine import UpdateEngine

_CACHE_DIR = Path("data/cache")
_OUTPUT_DIR = Path("data/outputs")
_MIN_DELAY_SECONDS = 1.0


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse competition results and write a point-update report."
    )
    parser.add_argument(
        "--result",
        dest="results",
        nargs=2,
        metavar=("URL", "DATE"),
        action="append",
        required=True,
        help="A results-page URL and its competition date (YYYY-MM-DD). "
        "Repeat for a backfill across multiple competitions.",
    )
    parser.add_argument(
        "--cache",
        dest="cache",
        action="store_true",
        default=True,
        help=f"Cache raw competition results data to {_CACHE_DIR}/ (default: enabled).",
    )
    parser.add_argument(
        "--no-cache",
        dest="cache",
        action="store_false",
        help="Don't cache raw competition results data.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)
    client = ThrottledClient(
        min_delay_seconds=_MIN_DELAY_SECONDS, cache_dir=_CACHE_DIR if args.cache else None
    )

    competitions = [
        parse_results_url(url, date.fromisoformat(date_str), client)
        for url, date_str in args.results
    ]

    engine = UpdateEngine()
    awards_per_competition = engine.run_backfill(competitions)
    all_awards = [award for comp_awards in awards_per_competition for award in comp_awards]

    starting_totals = engine.starting_totals()
    final_totals = {name: dancer.points for name, dancer in engine.final_totals().items()}
    report = build_report(all_awards, starting_totals, final_totals)
    text = render_report(report)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = _OUTPUT_DIR / f"{timestamp}-report.txt"
    output_path.write_text(text, encoding="utf-8")
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
