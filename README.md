# cda-tools: Tools for Officiating DanceSport Competitions

### Authors
Clifford Ashmun, CDA Board Member and Records Keeper

## Description
_Note: this project is a work in progress._

cda-tools is a repo for the [Collegiate Dancesport Association (CDA)](https://collegiatedancesport.org/) to automate
[Fair Level Certification (FLC)](https://collegiatedancesport.org/fairlevel/) at circuit dancesport competitions.

These tools aim to streamline the process of validating entries for dancers at member competitions and updating dancers' CDA FLC points after competitions,
ensuring that dancers' points are verified and updated in a timely manner and that competitions remain fun and fair for dancers of all levels of experience.

## Directory Structure

```
.
├── cda_core/                     # Core domain model & logic
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
│   │   │   └── multi_dance_expander.py  # Multi-dance abbreviation expansion
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
├── points_updating/                   # Point-calculation engine (parsing & DB writes not yet built)
│   ├── __init__.py
│   ├── lib/
│   │   ├── __init__.py
│   │   ├── update_engine.py      # UpdateEngine - process_competition()/run_backfill() orchestration
│   │   ├── points_calculator.py  # PointsCalculator - per-result scoring (Split-Level, cascade)
│   │   ├── report.py             # build_report()/render_report() - per-dancer point audit trail
│   │   ├── models/
│   │   │   └── result.py         #   CompetitionResult, DancerRef - format-agnostic result model
│   │   └── rules/
│   │       ├── award_table.py    #   compute_award() - CDA's placement x round depth point table
│   │       ├── cascade.py        #   build_cascade_delta() - commutes points down through levels
│   │       ├── eligibility_filter.py  # filter_points_eligible() - ignores Nightclub/Rookie-Vet
│   │       └── event_selection.py     # select_points_event_results() - open level multi-dance rule
│   └── tests/                    # Mirrors the lib/ tree above (see Test Organization below)
│       ├── test_update_engine.py
│       ├── test_points_calculator.py
│       ├── test_report.py
│       ├── models/
│       └── rules/
│
├── data/
│   └── inputs/                   # Competition entry CSVs (gitignored)
│
├── pyproject.toml                # Python package configuration (deps, build, entry points)
└── README.md
```

## Architecture Notes

### Constants (StrEnum)
All domain constants use Python 3.11+ `StrEnum` enums, so enum members work directly as strings without `.value` calls. See `cda_core/lib/constants.py` for available enums:
- `Style` — Standard, Smooth, Latin, Rhythm, Nightclub
- `SyllabusLevel` — Newcomer, Bronze, Silver, Gold
- `OpenLevel` — Novice, Prechamp, Champ
- `NightclubLevel` — Beginner, Intermediate/Advanced
- `RookieVetLevel` — Rookie Lead, Rookie Follow

### Rules Package
Proficiency/point-out calculations (`ProficiencyCalculator`) live directly in `cda_core/lib/`, since both `entry_checking` and `points_updating` need them. `entry_checking/lib/rules/` contains the entry-checking-specific logic built on top of that: partnership eligibility (including duplicate-entry and Nightclub consecutive-level checks), consecutive-level rules, and recommended-level suggestions. Validation logic returns structured `EligibilityResult` and `LevelViolation` dataclasses instead of printing directly, so results can be consumed by both the CLI and a future web UI.

### API Layer
API communication is isolated in `cda_core/lib/api/`. The `DancerRecord` dataclass provides typed access to CDA database responses. To use the API:
1. Copy `cda_core/lib/api/config.py.example` → `cda_core/lib/api/config.py`
2. Add your API key to `config.py`

### Competition & EntryChecker
`Competition` (`cda_core/lib/competition.py`) is a plain data model — it holds a competition's identity (name, date, rookie-vet ruleset, consecutive-level limit, and the Rookie's max regular-event level under the "newcomer" ruleset) and raw entry data, nothing else. Orchestration — building `Dancer`/`Partnership`/`Entry` objects from a `Competition`'s rows, running `EligibilityChecker` and `LevelRulesChecker`, and returning structured results — lives in `EntryChecker` (`entry_checking/lib/entry_checker.py`). Neither class prints; `entry_checker.main()` is the only place that prompts and prints. `EntryChecker.check_entry()`/`register_entry()` operate on a single partnership/dance pair (the building blocks `check()` is written in terms of), so a future live-registration caller could check/register one entry at a time instead of requiring a full CSV.

### Report View & Web UI
`entry_checking/lib/report_view.py`'s `build_report_view()` extracts the CLI's split-level-notes-then-grouped-violations presentation logic (previously embedded in `entry_checker._report()`'s `print()` calls) into a plain `ReportView` dataclass. `entry_checker._report()` is now a thin printer over it, and `entry_checking/lib/webapp/` (a lightweight Flask app, see Usage below) renders the same `ReportView` in HTML and JSON — one grouping algorithm, multiple consumers. `entry_checking/lib/webapp/` is deliberately scoped to entry checking; a more robust unified CDA app (e.g. also covering `points_updating`, possibly React/TypeScript) would be a separate top-level addition alongside it, not a replacement.

### Point Update Engine
`points_updating` is the calculation engine for CDA Fair Level Certification points — results parsing and the database write step are both intentionally out of scope for now (see below), so this is verifiable against real historical data (via the existing read-only `lookup_dancer()`) before write access is ever requested.

- **`CompetitionResult`/`DancerRef`** (`points_updating/lib/models/result.py`) is the format-agnostic intermediate model any future results parser is expected to produce — one `CompetitionResult` per (couple, dance, event), built on `Dance`'s existing normalization so scoring logic never needs to know which results source produced the raw strings.
- **`filter_points_eligible`** and **`select_points_event_results`** (`points_updating/lib/rules/`) are the pre-scoring pipeline: dropping non-points-eligible results (Nightclub, Rookie/Vet) and, for an open level split across more than one event (e.g. Novice Smooth run as a WTF event plus a separate V event), keeping only the event CDA rules use to calculate points.
- **`PointsCalculator.compute()`** (`points_updating/lib/points_calculator.py`) scores one `CompetitionResult` against a couple's current proficiency (via `ProficiencyCalculator`, shared with `entry_checking`): detecting the Split-Level Exception (tripling the award) and cascading the placement award down through lower levels (`award_table.py`/`cascade.py`) into a `ResultAward`.
- **`UpdateEngine`** (`points_updating/lib/update_engine.py`) is the orchestrator. `process_competition()` scores every result in one competition against the ledger's state as of immediately before that competition — never against points earned earlier in the same competition, so Split-Level detection can't depend on processing order — then applies every resulting delta. `run_backfill()` repeats that per competition across an already-sorted (it sorts internally) list of competitions, each building on the ledger state the last left behind. The dancer lookup is an injected dependency (defaulting to the real CDA API), so tests don't need a network call or a test database.
- **`build_report()`/`render_report()`** (`points_updating/lib/report.py`) turn a set of `ResultAward`s plus `UpdateEngine.starting_totals()`/`final_totals()` into a per-dancer audit trail — every result that contributed to a point change (including zero-point placements), so an unexpected total can be traced back to the exact result that produced it, or explained to a dancer who asks.

### Import Convention
All internal imports are absolute package paths (`from cda_core.lib.models.dance import Dance`, `from entry_checking.lib.rules.eligibility_checker import EligibilityChecker`), not `sys.path` manipulation. This means `cda_core`, `entry_checking`, and `points_updating` need to be resolvable as real top-level packages — either via `pip install -e .` (see Setup), or by running from the repo root, where Python's `-m` flag adds the current directory to `sys.path` automatically.

### Test Organization
In `cda_core`, `entry_checking`, and `points_updating`, `tests/` mirrors the shape of `lib/` — a module directly under `lib/` (e.g. `entry_checking/lib/entry_checker.py`) has its test directly under `tests/` (`entry_checking/tests/test_entry_checker.py`), and a subpackage under `lib/` (e.g. `cda_core/lib/models/`, `entry_checking/lib/rules/`) has a matching subdirectory under `tests/` (`cda_core/tests/models/`, `entry_checking/tests/rules/`) holding its tests. Test files are also named after the module they test - `cda_core/lib/api/client.py` is tested by `cda_core/tests/api/test_client.py`, not `test_api_client.py` - so a module covering several source files (e.g. the `parsing/` package) gets one test file per source file (`test_csv_reader.py`, `test_row_parser.py`, `test_multi_dance_expander.py`) rather than one combined file. This makes it easy to find a module's tests (and vice versa) purely from its path, without needing to guess at a naming convention.

## Usage

### CLI Entry Checker
```bash
# Via entry point (requires `pip install -e .`)
entry-checker

# Or via -m, from the repo root (no install required)
python -m entry_checking.lib.entry_checker
```

> Running `entry_checking/lib/entry_checker.py` directly (without `-m`) will NOT work — only the
> script's own directory ends up on `sys.path`, not the repo root, so `cda_core` won't resolve. Use one
> of the two forms above.

### Web UI
```bash
# Via entry point (requires `pip install -e .`)
entry-checker-web
# Then open http://127.0.0.1:5000/ in a browser

# Or, for auto-reload while developing templates/routes:
flask --app entry_checking.lib.webapp.app:create_app run --debug --reload
```

Both commands work from any directory once `pip install -e .` has been run — the editable
install is what makes `entry_checking` importable, not the working directory. (Unlike the CLI's
`-m` fallback below, there's no repo-root-relative form here, since Flask's dev server needs the
app importable as a real package either way.)

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

## Setup

```bash
# Install in development mode (required for the `entry-checker` console script;
# `python -m unittest discover` and `python -m entry_checking.lib.entry_checker`
# work from the repo root without this, since -m puts the repo root on sys.path)
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

`pytest` just gives nicer output and is the recommended way to run them.

## Linting, Formatting & Type Checking

```bash
black .          # auto-format
flake8           # style/unused-import checks (config in .flake8)
mypy cda_core entry_checking points_updating  # type checking (config in pyproject.toml)
```

`black`'s line length is set to 100 in `pyproject.toml` (`[tool.black]`) to match `flake8`'s
`max-line-length` in `.flake8` — the two are kept in agreement deliberately.

## Running All Checks

```bash
python scripts/check.py
```

Runs `black --check`, `flake8`, `mypy`, and `pytest` in sequence, printing a pass/fail summary at
the end. Doesn't stop at the first failure, so one run surfaces everything that needs fixing.
