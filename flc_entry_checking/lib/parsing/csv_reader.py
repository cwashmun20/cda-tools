"""CSV reading and column validation for competition entry spreadsheets.

Provides functions for reading competition entry data from CSV files,
validating required columns, and normalizing column name variations.
"""

from typing import Optional

import pandas as pd


# Required columns for a valid competition entry spreadsheet
REQUIRED_COLUMNS = ["Style", "Dance", "Skill", "Lead First", "Lead Last",
                    "Follow First", "Follow Last"]

# Optional columns that may appear
OPTIONAL_COLUMNS = ["O2CM Name", "Heat", "O2CM Div"]

# Column name aliases for normalization
COLUMN_ALIASES = {
    "Leader First": "Lead First",
    "Leader Last": "Lead Last",
    "Follower First": "Follow First",
    "Follower Last": "Follow Last",
    "Lead 1 First": "Lead First",
    "Lead 1 Last": "Lead Last",
    "Follow 1 First": "Follow First",
    "Follow 1 Last": "Follow Last",
}


def read_entries(path: str) -> pd.DataFrame:
    """Read a competition entry CSV file and return a DataFrame.

    Args:
        path: Path to the CSV file.
    Returns:
        A pandas DataFrame with the entry data.
    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If required columns are missing.
    """
    df = pd.read_csv(path)
    df = normalize_column_names(df)
    validate_columns(df)
    return df


def validate_columns(df: pd.DataFrame) -> bool:
    """Validate that a DataFrame has all required columns.

    Args:
        df: The DataFrame to validate.
    Returns:
        True if all required columns are present.
    Raises:
        ValueError: If any required columns are missing.
    """
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required columns: {', '.join(missing)}. "
            f"Found columns: {', '.join(df.columns.tolist())}"
        )
    return True


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to handle alternate naming conventions.

    For example, "Leader First" becomes "Lead First".

    Args:
        df: DataFrame with potentially non-standard column names.
    Returns:
        DataFrame with normalized column names.
    """
    rename_map = {}
    for col in df.columns:
        if col in COLUMN_ALIASES:
            rename_map[col] = COLUMN_ALIASES[col]
    if rename_map:
        df = df.rename(columns=rename_map)
    return df