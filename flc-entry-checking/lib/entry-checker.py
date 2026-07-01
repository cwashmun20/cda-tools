"""Entry checker CLI for CDA Fair Level Certification.

Usage:
    python -m flc_entry_checking.lib.entry_checker
    
    (or via installed entry point: entry-checker)
"""

import sys
import os

# Allow imports from cda-core/lib when running as script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'cda-core', 'lib'))

import competition  # type: ignore


def main():
    """Run the entry checker, prompting for a CSV file path."""
    path = input("Please enter full path of entry spreadsheet (with file extension): ")
    comp = competition.Competition(path)
    comp.check_entries()


if __name__ == "__main__":
    main()