# cda-tools: Tools for Officiating DanceSport Competitions

### Authors
Clifford Ashmun, CDA Board Member and Records Keeper

## Overview

cda-tools automates [Fair Level Certification (FLC)](https://collegiatedancesport.org/fairlevel/)
for the [Collegiate Dancesport Association (CDA)](https://collegiatedancesport.org/) at circuit
dancesport competitions. It validates dancer entries against FLC rules and updates dancers' CDA
FLC points after competitions, keeping points current and competitions fair across all experience
levels.

## Usage

### CLI Entry Checker
```bash
# Via entry point (requires `pip install -e .`)
entry-checker

# Or via -m, from the repo root (no install required)
python -m entry_checking.lib.entry_checker
```

> Running `entry_checking/lib/entry_checker.py` directly (without `-m`) will NOT work — only the
> script's own directory ends up on `sys.path`, not the repo root, so `utils` won't resolve. Use one
> of the two forms above.

### Web UI
```bash
# Via entry point (requires `pip install -e .`)
entry-checker-web
# Then open http://127.0.0.1:5000/ in a browser

# Or, for auto-reload while developing templates/routes:
flask --app entry_checking.lib.webapp.app:create_app run --debug --reload
```

Both commands work from any directory once you've run `pip install -e .` — the editable install is
what makes `entry_checking` importable, not the working directory. Unlike the CLI's `-m` fallback
above, there's no repo-root-relative form here, since Flask's dev server needs the app importable
as a real package either way.

Either command runs the dev server in the foreground of the terminal it was started in — press
**Ctrl+C** in that terminal to stop it. If it was started in the background (e.g. `entry-checker-web &`)
or the terminal was closed while it kept running, find and stop the listening process instead:

```bash
# Windows (from Git Bash/PowerShell): find the PID bound to port 5000, then kill it
netstat -ano | findstr :5000
taskkill /F /PID <pid>

# macOS/Linux
lsof -i :5000
kill <pid>
```

A single-page form (competition details + CSV upload) that runs the same
`EntryChecker` used by the CLI and renders the results as split-level notes
followed by violations grouped by dancer/partnership. `POST /api/check`
exposes the same check as JSON, for future programmatic callers.

### Points Updating CLI
```bash
# Via entry point (requires `pip install -e .`)
points-updater --result <results-page-url> <competition-date>

# Or via -m, from the repo root (no install required)
python -m points_updating.lib.cli --result <results-page-url> <competition-date>
```

Example — one competition:
```bash
points-updater --result "https://results.o2cm.com/event3.asp?event=isc25" 2025-11-14
```

Example — a chronological backfill across several competitions in one run (order given doesn't
matter; `UpdateEngine` sorts by date before scoring):
```bash
points-updater \
  --result "https://ballroomcompexpress.com/results.php?cid=178" 2025-10-25 \
  --result "https://results.o2cm.com/event3.asp?event=isc25" 2025-11-14
```

`--result` takes a competition's results-page URL — O2CM, Ballroom Comp Express, or a school's
`*.dance.am` results page — and that competition's date (`YYYY-MM-DD`). `routing.py` determines which parser to use from the URL alone. Repeat `--result` for a multi-competition backfill.

Raw fetched results are cached to `data/cache/` by default, so re-running against the same
competition doesn't re-hit the live site; pass `--no-cache` to disable. The rendered report is
always written to `data/outputs/<timestamp>-report.txt` — one section per dancer with their
starting and final point totals followed by every result that contributed to the change between
them (including zero-point placements).

> Same `-m` restriction as the entry checker — running `points_updating/lib/cli.py` directly won't
> work. Use one of the two forms above.

Fetching real results is deliberately rate-limited (`ThrottledClient`, shared across every source
in one run). O2CM fetches a whole competition in a single request; Ballroom Comp Express and
CompOrganizer fetch one request per event, so a large competition on either of those can still mean
a couple of minutes of live requests, not a quick check.

### Points Updating Web UI
```bash
# Via entry point (requires `pip install -e .`)
points-updater-web
# Then open http://127.0.0.1:5000/ in a browser

# Or, for auto-reload while developing templates/routes:
flask --app points_updating.lib.webapp.app:create_app run --debug --reload
```

Paste one or more results-page links, each with the date that competition was danced on (use
"+ Add another link" for a backfill across several competitions), then run the update. The page is
a full synchronous submit — like the CLI, a large competition can take a few minutes, so the button
shows a "Running..." state for the duration rather than looking stuck.

A **Dry run** checkbox (checked by default) sits above the Run Update button. Since the database
write step doesn't exist yet (see Point Update Engine below), unchecking it and submitting returns
a clear error instead of silently behaving like a dry run.

Once results load, the page switches to a **Results** tab (freely toggled back to **Input** without
losing either) showing how many dancers weren't already in the CDA database (and would be newly
created), followed by every dancer's starting/final totals and contributing results, in the same
format as the CLI's output file. A dropdown — sorted by last name, with "Show all updates" as the
default — filters the view to one dancer at a time, entirely client-side (no server round-trip). A
**Download as .txt** button saves whatever's currently visible (all dancers or just the selected
one) exactly as shown.

Runs in the foreground of its terminal (**Ctrl+C** to stop); if it outlives its terminal, stop it
the same way as the entry-checker's Web UI above. Flask's dev server defaults to port 5000 for
both — don't run this alongside the entry-checker Web UI without changing one's port
(`flask run --port 5001`, or `create_app().run(port=5001)`).

## Setup

```bash
# Installs in development mode. Required for the `entry-checker` console script;
# `-m` invocations work without it — see "Import Convention" below for why.
pip install -e .

# Or, to also install dev dependencies (pytest, black, flake8, mypy):
pip install -e ".[dev]"
```

## Testing

```bash
pytest
```

Tests are written against `unittest.TestCase` (no `pytest`-specific fixtures), so they also run without installing `pytest` at all:

```bash
python -m unittest discover
```

`pytest` gives nicer output and is the recommended way to run them.

## Linting, Formatting & Type Checking

```bash
black .          # auto-format
flake8           # style/unused-import checks (config in .flake8)
mypy utils entry_checking points_updating  # type checking (config in pyproject.toml)
```

`black`'s line length is set to 100 in `pyproject.toml` (`[tool.black]`) to match `flake8`'s
`max-line-length` in `.flake8` — the two are kept in agreement deliberately.

## Running All Checks

```bash
python scripts/check.py
```

Runs `black --check`, `flake8`, `mypy`, and `pytest` in sequence, printing a pass/fail summary at
the end. Doesn't stop at the first failure, so one run surfaces everything that needs fixing.

## Directory Structure

```
.
├── utils/                     # Core domain model & logic
│   ├── __init__.py
│   ├── lib/
│   │   ├── competition.py        # Competition data model (name, date, ruleset, raw entries)
│   │   ├── constants.py          # Enums & typed constants (StrEnum)
│   │   ├── points.py             # Points tracking & formatting
│   │   ├── proficiency_calculator.py  # ProficiencyCalculator - shared by entry_checking & points_updating
│   │   ├── api/                  # CDA points database API client
│   │   │   ├── client.py         #   DancerRecord, lookup_dancer()
│   │   │   └── config.py.example #   API key template
│   │   └── models/               # Domain model classes
│   │       ├── dance.py          #   Dance representation & conversion
│   │       ├── dancer.py         #   Dancer (points, registration state)
│   │       ├── partnership.py    #   Partnership (registration state)
│   │       ├── entry.py          #   Competition entry
│   │       └── event.py          #   Competition event
│   └── tests/                    # Mirrors the lib/ tree above (see Test Organization below)
│       ├── test_constants.py
│       ├── test_points.py
│       ├── api/
│       └── models/
│
├── entry_checking/           # Entry validation: orchestration, rules, parsing
│   ├── __init__.py
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── entry_checker.py      # EntryChecker orchestration + CLI entry point
│   │   ├── report_view.py        # Presentation-agnostic report grouping (shared by CLI & web UI)
│   │   ├── parsing/              # Input parsing (CSV, multi-dance)
│   │   │   ├── csv_reader.py     #   CSV reading & column validation
│   │   │   ├── row_parser.py     #   Per-row data extraction
│   │   │   └── multi_dance_resolver.py  # Multi-dance abbreviation resolution
│   │   ├── rules/                # FLC rule checking
│   │   │   ├── violations.py     #   ViolationType, EligibilityResult, LevelViolation
│   │   │   ├── recommended_levels_calculator.py  # RecommendedLevelsCalculator
│   │   │   ├── eligibility_checker.py  # EligibilityChecker
│   │   │   └── level_rules_checker.py  # LevelRulesChecker
│   │   └── webapp/               # Lightweight Flask UI, scoped to entry checking
│   │       ├── app.py            #   create_app() factory + web console-script entry point
│   │       ├── routes.py         #   HTML form/results route + JSON /api/check route
│   │       ├── check_service.py  #   Shared parse -> Competition -> EntryChecker.check() helper
│   │       ├── templates/
│   │       └── static/
│   └── tests/                    # Mirrors the lib/ tree above (see Test Organization below)
│       ├── test_entry_checker.py
│       ├── parsing/
│       ├── rules/
│       └── webapp/
│
├── points_updating/                   # Point-calculation engine, results parsing, and CLI (DB writes not yet built)
│   ├── __init__.py
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── cli.py                # CLI: parses results, scores them, writes a report (see Usage)
│   │   ├── update_engine.py      # UpdateEngine - process_competition()/run_backfill() orchestration
│   │   ├── points_calculator.py  # PointsCalculator - per-result scoring (Split-Level, cascade)
│   │   ├── report.py             # build_report()/render_report() - per-dancer point audit trail
│   │   ├── models/
│   │   │   └── result.py         #   CompetitionResult, DancerRef - format-agnostic result model
│   │   ├── parsing/               # Results-source parsing (one module per source) + URL routing
│   │   │   ├── http_client.py    #   ThrottledClient - shared rate-limited, cacheable HTTP client
│   │   │   ├── comporganizer.py  #   CompOrganizer/dance.am parser
│   │   │   ├── ballroom_comp_express.py  # Ballroom Comp Express parser
│   │   │   ├── o2cm.py           #   O2CM parser
│   │   │   └── routing.py        #   parse_results_url() - routes a URL to its source parser
│   │   ├── rules/
│   │   │   ├── award_table.py    #   compute_award() - CDA's placement x round depth point table
│   │   │   ├── cascade.py        #   build_cascade_delta() - cascades points down through levels
│   │   │   ├── eligibility_filter.py  # filter_points_eligible() - ignores Nightclub/Rookie-Vet
│   │   │   └── event_selection.py     # select_points_event_results() - open level multi-dance rule
│   │   └── webapp/               # Lightweight Flask UI, scoped to points updating
│   │       ├── app.py            #   create_app() factory + web console-script entry point
│   │       ├── routes.py         #   HTML form/results route
│   │       ├── update_service.py #   Shared parse -> UpdateEngine -> report helper
│   │       ├── templates/
│   │       └── static/
│   └── tests/                    # Mirrors the lib/ tree above (see Test Organization below)
│       ├── test_update_engine.py
│       ├── test_points_calculator.py
│       ├── test_report.py
│       ├── test_parsing_to_engine_integration_*.py  # parsing -> UpdateEngine -> report, one file per source
│       ├── models/
│       ├── parsing/
│       │   └── fixtures/         #   Real, captured/trimmed source data - no live calls in tests
│       ├── rules/
│       └── webapp/
│
├── data/
│   ├── inputs/                   # Competition entry CSVs (gitignored)
│   ├── outputs/                  # Point-update reports written by the CLI (gitignored)
│   └── cache/                    # Cached raw results data, if the CLI's --cache is on (gitignored)
│
├── pyproject.toml                # Python package configuration (deps, build, entry points)
└── README.md
```

## Architecture & Design Notes

### Import Convention
All internal imports are absolute package paths (`from utils.lib.models.dance import Dance`, `from entry_checking.lib.rules.eligibility_checker import EligibilityChecker`), not `sys.path` manipulation. This means `utils`, `entry_checking`, and `points_updating` need to be resolvable as real top-level packages — either via `pip install -e .` (see Setup), or by running from the repo root, where Python's `-m` flag adds the current directory to `sys.path` automatically.

### Test Organization
In `utils`, `entry_checking`, and `points_updating`, `tests/` mirrors the shape of `lib/` — a module directly under `lib/` (e.g. `entry_checking/lib/entry_checker.py`) has its test directly under `tests/` (`entry_checking/tests/test_entry_checker.py`), and a subpackage under `lib/` (e.g. `utils/lib/models/`, `entry_checking/lib/rules/`) has a matching subdirectory under `tests/` (`utils/tests/models/`, `entry_checking/tests/rules/`) holding its tests. Test files are also named after the module they test - `utils/lib/api/client.py` is tested by `utils/tests/api/test_client.py`, not `test_api_client.py` - so a module covering several source files (e.g. the `parsing/` package) gets one test file per source file (`test_csv_reader.py`, `test_row_parser.py`, `test_multi_dance_resolver.py`) rather than one combined file. This makes it easy to find a module's tests (and vice versa) purely from its path, without needing to guess at a naming convention.

### Constants (StrEnum)
All domain constants use Python 3.11+ `StrEnum` enums, so enum members work directly as strings without `.value` calls. See `utils/lib/constants.py` for available enums:
- `Style` — Standard, Smooth, Latin, Rhythm, Nightclub
- `SyllabusLevel` — Newcomer, Bronze, Silver, Gold
- `OpenLevel` — Novice, Prechamp, Champ
- `NightclubLevel` — Beginner, Intermediate/Advanced
- `RookieVetLevel` — Rookie Lead, Rookie Follow

### API Layer
API communication is isolated in `utils/lib/api/`. The `DancerRecord` dataclass provides typed access to CDA database responses. To use the API:
1. Copy `utils/lib/api/config.py.example` → `utils/lib/api/config.py`
2. Add your API key to `config.py`

### Rules Package
Proficiency/point-out calculations (`ProficiencyCalculator`) live directly in `utils/lib/`, since both `entry_checking` and `points_updating` need them. `entry_checking/lib/rules/` contains the entry-checking-specific logic built on top of that: partnership eligibility (including duplicate-entry and Nightclub consecutive-level checks), consecutive-level rules, and recommended-level suggestions. Validation logic returns structured `EligibilityResult` and `LevelViolation` dataclasses instead of printing directly, so results can be consumed by both the CLI and a future web UI.

### Competition & EntryChecker
`Competition` (`utils/lib/competition.py`) is a plain data model — it holds a competition's identity (name, date, rookie-vet ruleset, consecutive-level limit, and the Rookie's max regular-event level under the "newcomer" ruleset) and raw entry data, nothing else. Orchestration — building `Dancer`/`Partnership`/`Entry` objects from a `Competition`'s rows, running `EligibilityChecker` and `LevelRulesChecker`, and returning structured results — lives in `EntryChecker` (`entry_checking/lib/entry_checker.py`). Neither class prints; `entry_checker.main()` is the only place that prompts and prints. `EntryChecker.check_entry()`/`register_entry()` operate on a single partnership/dance pair (the building blocks `check()` is written in terms of), so a future live-registration caller could check/register one entry at a time instead of requiring a full CSV.

### Report View & Web UI
`entry_checking/lib/report_view.py`'s `build_report_view()` extracts the CLI's split-level-notes-then-grouped-violations presentation logic into a plain `ReportView` dataclass. `entry_checker._report()` is a thin printer over it, and `entry_checking/lib/webapp/` (a lightweight Flask app, see Usage above) renders the same `ReportView` in HTML and JSON — one grouping algorithm, multiple consumers. `entry_checking/lib/webapp/` is deliberately scoped to entry checking; a more robust unified CDA app (e.g. also covering `points_updating`, possibly React/TypeScript) would be a separate top-level addition alongside it, not a replacement.

### Point Update Engine
`points_updating` parses real competition results, calculates the FLC points they earn, and writes a human-readable report. Writing to the database is the one piece intentionally out of scope — everything up to that point can be verified against real historical data via the existing read-only `lookup_dancer()`, before write access is requested.

- **`CompetitionResult`/`DancerRef`** (`points_updating/lib/models/result.py`) — the format-agnostic result model every parser produces, one per (couple, event), so scoring logic doesn't need to know which source produced it.
- **`points_updating/lib/parsing/`** — one parser per results source used on the CDA circuit: O2CM (`o2cm.py`), Ballroom Comp Express (`ballroom_comp_express.py`), and CompOrganizer (`comporganizer.py`, see its docstring for the `*.dance.am` template variants it handles). All three share `http_client.py`'s rate-limited `ThrottledClient`, since each fetches from a live third-party site. `routing.py`'s `parse_results_url()` picks the right parser from a results-page URL.
- **`filter_points_eligible`**/**`select_points_event_results`** (`points_updating/lib/rules/`) — the pre-scoring pipeline: drops non-points-eligible results (Nightclub, Rookie/Vet), then narrows an open level split across multiple events down to the one CDA rules use for points (see `event_selection.py`).
- **`PointsCalculator.compute()`** (`points_updating/lib/points_calculator.py`) — scores one `CompetitionResult` against a couple's current proficiency, detecting the Split-Level Exception and cascading the placement award down through lower levels (see `award_table.py`/`cascade.py` for the cascade mechanics).
- **`UpdateEngine`** (`points_updating/lib/update_engine.py`) — orchestrates scoring. `process_competition()` scores one competition against the ledger's state as of just before it (see its docstring for why); `run_backfill()` repeats that across a sorted list of competitions.
- **`build_report()`/`render_report()`** (`points_updating/lib/report.py`) — turns scored results into a per-dancer audit trail of starting/final totals and every contributing result (see the module docstring).
- **`points_updating/lib/cli.py`** (see Usage above) — wires `routing.py` → `UpdateEngine` → `report.py` into a runnable command.
- **`points_updating/lib/webapp/`** (see Usage above) — a second consumer of the same pipeline; `update_service.py`'s `run_update()` is the shared entry point, mirroring `entry_checking/lib/webapp/check_service.py`.
