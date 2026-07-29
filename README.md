# cda-tools: Fair Level Certification Made Simple

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
├── cda-core/                     # Core domain model & logic
│   ├── __init__.py
│   └── lib/
│       ├── competition.py        # Competition data model (name, date, ruleset, raw entries)
│       ├── constants.py          # Enums & typed constants (StrEnum)
│       ├── points.py             # Points tracking & formatting
│       ├── api/                  # CDA points database API client
│       │   ├── client.py         #   DancerRecord, lookup_dancer()
│       │   └── config.py.example #   API key template
│       ├── models/               # Domain model classes
│       │   ├── dance.py          #   Dance representation & conversion
│       │   ├── dancer.py         #   Dancer (points, registration state)
│       │   ├── partnership.py    #   Partnership (registration state)
│       │   ├── entry.py          #   Competition entry
│       │   └── event.py          #   Competition event
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
├── flc-entry-checking/           # CLI tool for entry validation
│   ├── __init__.py
│   └── lib/
│       ├── __init__.py
│       └── entry_checker.py      # EntryChecker orchestration + CLI entry point
│
├── flc-points/                   # Points updating tool (to be implemented)
│   ├── __init__.py
│   └── lib/
│       └── __init__.py
│
├── data/
│   └── inputs/                   # Competition entry CSVs (gitignored)
│
├── setup.py                      # Python package configuration
├── requirements.txt              # Pinned dependencies
└── README.md
```

## Architecture Notes

### Constants (StrEnum)
All domain constants use Python 3.11+ `StrEnum` enums, so enum members work directly as strings without `.value` calls. See `cda-core/lib/constants.py` for available enums:
- `Style` — Standard, Smooth, Latin, Rhythm, Nightclub
- `SyllabusLevel` — Newcomer, Bronze, Silver, Gold
- `OpenLevel` — Novice, Prechamp, Champ
- `NightclubLevel` — Beginner, IntAdv
- `RookieVetLevel` — RkLead, RkFollow

### Rules Package
Validation logic returns structured `EligibilityResult` and `LevelViolation` dataclasses instead of printing directly. This allows results to be consumed by both the CLI and future web UI.

### API Layer
API communication is isolated in `cda-core/lib/api/`. The `DancerRecord` dataclass provides typed access to CDA database responses. To use the API:
1. Copy `cda-core/lib/api/config.py.example` → `cda-core/lib/api/config.py`
2. Add your API key to `config.py`

### Competition & EntryChecker
`Competition` (`cda-core/lib/competition.py`) is a plain data model — it holds a competition's identity (name, date, ruleset) and raw entry data, nothing else. Orchestration — building `Dancer`/`Partnership`/`Entry` objects from a `Competition`'s rows, running `EligibilityChecker` and `LevelRulesChecker`, and returning structured results — lives in `EntryChecker` (`flc-entry-checking/lib/entry_checker.py`). Neither class prints; `entry_checker.main()` is the only place that prompts and prints, so the same orchestration can later be reused by a non-interactive caller (e.g. a web UI).

## Usage

### CLI Entry Checker
```bash
# Via entry point (when installed)
entry-checker

# Or directly
python -m flc_entry_checking.lib.entry_checker
```

> **Known issue:** `pip install -e .` currently installs via setuptools' legacy
> "develop" mode, which does not honor `setup.py`'s `package_dir` mapping from
> hyphenated directories (`cda-core`, `flc-entry-checking`, `flc-points`) to
> their underscored import names. That means `cda_core`/`flc_entry_checking`/
> `flc_points` are not actually importable after an editable install, and the
> `entry-checker` console script currently fails at import time. Until the
> directories are renamed to match their import names (or the packaging setup
> is otherwise reworked), run the CLI directly instead:
> ```bash
> python flc-entry-checking/lib/entry_checker.py
> ```

## Setup

```bash
# Install in development mode
pip install -e .

# Or install dependencies manually
pip install -r requirements.txt