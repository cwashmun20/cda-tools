#!/usr/bin/env python3
"""Run all code-quality checks: black, flake8, mypy, and the test suite.

Runs every check even if an earlier one fails, then prints a pass/fail
summary - so a single run surfaces everything that needs fixing instead of
stopping at the first failure.

Usage:
    python scripts/check.py
"""

import subprocess
import sys

CHECKS = [
    ("black", ["black", "--check", "."]),
    ("flake8", ["flake8", "cda_core", "flc_entry_checking", "flc_points"]),
    ("mypy", ["mypy", "cda_core", "flc_entry_checking", "flc_points"]),
    ("pytest", ["pytest"]),
]


def main() -> int:
    results = []
    for name, cmd in CHECKS:
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run([sys.executable, "-m", *cmd])
        results.append((name, result.returncode == 0))

    print("\n=== Summary ===")
    all_passed = True
    for name, passed in results:
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
        all_passed = all_passed and passed

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
