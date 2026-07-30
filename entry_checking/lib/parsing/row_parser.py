"""Per-row parsing for competition entry spreadsheets.

Provides functions for detecting TBA rows, extracting dancer names,
and creating structured entry data from CSV rows.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class EntryData:
    """Structured data extracted from a single competition entry row."""

    style: str
    dance_name: str
    level: str
    lead_first: str
    lead_last: str
    follow_first: str
    follow_last: str
    heat: Optional[str] = None


def _is_missing(value) -> bool:
    """Checks whether a single cell value represents a missing name.

    Catches both a true NaN (Pandas' representation of an empty cell) and
    organizers who write the literal string "NULL" instead of leaving the
    cell blank.
    """
    if type(value) is float:
        return True
    return isinstance(value, str) and value.strip().upper() == "NULL"


def is_tba_row(row) -> bool:
    """Checks whether an entry row is a TBA entry (missing a lead or follow name).

    Args:
        row: A pandas Series representing a single CSV row.
    Returns:
        True if either lead or follow name is missing.
    """
    missing_lead = _is_missing(row.get("Lead First")) or _is_missing(row.get("Lead Last"))
    missing_follow = _is_missing(row.get("Follow First")) or _is_missing(row.get("Follow Last"))
    return missing_lead or missing_follow


def parse_dancer_names(row) -> tuple[str, str]:
    """Extract lead and follow full names from a row.

    Args:
        row: A pandas Series representing a single CSV row.
    Returns:
        A tuple of (lead_name, follow_name) as full names.
    """
    lead_name = str(row["Lead First"]) + " " + str(row["Lead Last"])
    follow_name = str(row["Follow First"]) + " " + str(row["Follow Last"])
    return lead_name, follow_name


def extract_entry(row, heat: Optional[str] = None) -> EntryData:
    """Extract structured entry data from a CSV row.

    Args:
        row: A pandas Series representing a single CSV row.
        heat: Optional heat number.
    Returns:
        An EntryData dataclass with the extracted fields.
    """
    return EntryData(
        style=row["Style"],
        dance_name=row["Dance"],
        level=row["Skill"],
        lead_first=row["Lead First"],
        lead_last=row["Lead Last"],
        follow_first=row["Follow First"],
        follow_last=row["Follow Last"],
        heat=heat,
    )
