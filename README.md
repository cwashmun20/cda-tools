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
│   └── lib/
│       ├── competition.py        # Competition data model (name, date, ruleset, raw entries)
│       ├── constants.py          # Enums & typed constants (StrEnum)
│       ├── points.py             # Points tracking & formatting
│       ├── api/                  # CDA points database API client
│       │   ├── client.py         #   DancerRecord, lookup_dancer()
│       │   └── config.py.example #   API key template
│       └── models/               # Domain model classes
│           ├── dance.py          #   Dance representation & conversion
│           ├── dancer.py         #   Dancer (points, registration state)
│           ├── partnership.py    #   Partnership (registration state)
│           ├── entry.py          #   Competition entry
│           └── event.py          #   Competition event
│
├── entry_checking/           # Entry validation: orchestration, rules, parsing
│   ├── __init__.py
│   └── lib/
│       ├── __init__.py
│       ├── entry_checker.py      # EntryChecker orchestration + CLI entry point
│       ├── parsing/              # Input parsing (CSV, multi-dance)
│       │   ├── csv_reader.py     #   CSV reading & column validation
│       │   ├── row_parser.py     #   Per-row data extraction
│       │   └── multi_dance_expander.py  # Multi-dance abbreviation expansion
│       └── rules/                # FLC rule checking
│           ├── violations.py     #   ViolationType, EligibilityResult
│           ├── proficiency.py    #   ProficiencyCalculator
│           ├── eligibility.py    #   EligibilityChecker
│           └── level_rules.py    #   LevelRulesChecker
│
├── points_updating/                   # Points updating tool (to be implemented)
│   ├── __init__.py
│   └── lib/
│       └── __init__.py
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
`entry_checking/lib/rules/` contains FLC validation logic (proficiency, eligibility, consecutive-level rules). It operates on `cda_core` domain objects (`Dancer`, `Partnership`, `Dance`) but lives outside `cda_core` since it's entry-checking-specific, not core domain. Validation logic returns structured `EligibilityResult` and `LevelViolation` dataclasses instead of printing directly, so results can be consumed by both the CLI and a future web UI.

### API Layer
API communication is isolated in `cda_core/lib/api/`. The `DancerRecord` dataclass provides typed access to CDA database responses. To use the API:
1. Copy `cda_core/lib/api/config.py.example` → `cda_core/lib/api/config.py`
2. Add your API key to `config.py`

### Competition & EntryChecker
`Competition` (`cda_core/lib/competition.py`) is a plain data model — it holds a competition's identity (name, date, ruleset) and raw entry data, nothing else. Orchestration — building `Dancer`/`Partnership`/`Entry` objects from a `Competition`'s rows, running `EligibilityChecker` and `LevelRulesChecker`, and returning structured results — lives in `EntryChecker` (`entry_checking/lib/entry_checker.py`). Neither class prints; `entry_checker.main()` is the only place that prompts and prints, so the same orchestration can later be reused by a non-interactive caller (e.g. a web UI).

### Import Convention
All internal imports are absolute package paths (`from cda_core.lib.models.dance import Dance`, `from entry_checking.lib.rules.eligibility import EligibilityChecker`), not `sys.path` manipulation. This means `cda_core` and `entry_checking` need to be resolvable as real top-level packages — either via `pip install -e .` (see Setup), or by running from the repo root, where Python's `-m` flag adds the current directory to `sys.path` automatically.

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
