"""
Stage3 Calendar Column Generator
--------------------------------

This module performs the following operations:

1. Load the selected date range from calendar_period.json.
2. Load all CSV files inside plant_information_sheet.
3. Add calendar columns (one column per day) using Polars for high performance.
4. Convert encoding between UTF-8-SIG and UTF-8 as needed.

This script is intended to be used as part of the Stage3 pipeline
in the Data Preprocessing Pipeline project.

Author: YOUR_NAME
Repository: https://github.com/yourname/yourrepo
"""

from pathlib import Path
from datetime import datetime, timedelta
import json
import polars as pl


# ==============================================================================
# Utility Functions
# ==============================================================================

def add_calendar_columns(df: pl.DataFrame,
                         start_date: datetime.date,
                         end_date: datetime.date) -> pl.DataFrame:
    """
    Add daily calendar columns (YYYY-MM-DD) to a Polars DataFrame.

    Parameters
    ----------
    df : pl.DataFrame
        Input DataFrame.
    start_date : date
        Start of calendar range.
    end_date : date
        End of calendar range.

    Returns
    -------
    pl.DataFrame
        DataFrame with added calendar columns.
    """
    current = start_date
    while current <= end_date:
        col_name = current.strftime("%Y-%m-%d")
        df = df.with_columns(pl.lit("").alias(col_name))
        current += timedelta(days=1)
    return df


def load_period(period_file: Path) -> tuple[datetime.date, datetime.date]:
    """
    Load calendar period from JSON file.

    Parameters
    ----------
    period_file : Path
        Path to calendar_period.json.

    Returns
    -------
    tuple[date, date]
        (start_date, end_date)
    """
    if not period_file.exists():
        raise FileNotFoundError("calendar_period.json が存在しません。")

    with period_file.open("r", encoding="utf-8") as f:
        period = json.load(f)

    start = datetime.strptime(period["start"], "%Y-%m-%d").date()
    end = datetime.strptime(period["end"], "%Y-%m-%d").date()

    return start, end


def convert_to_utf8(file: Path) -> None:
    """
    Convert UTF-8-SIG → UTF-8 (no BOM).

    Parameters
    ----------
    file : Path
        CSV file path.
    """
    text = file.read_text(encoding="utf-8-sig")
    file.write_text(text, encoding="utf-8")


def convert_to_utf8_sig(file: Path) -> None:
    """
    Convert UTF-8 → UTF-8-SIG.

    Parameters
    ----------
    file : Path
        CSV file path.
    """
    text = file.read_text(encoding="utf-8")
    file.write_text(text, encoding="utf-8-sig")


def process_csv_file(file: Path,
                     start_date: datetime.date,
                     end_date: datetime.date) -> None:
    """
    Add calendar columns to a single CSV file using Polars.

    Parameters
    ----------
    file : Path
        CSV file path.
    start_date : date
        Start of calendar range.
    end_date : date
        End of calendar range.
    """
    print(f"処理中：{file.name}")

    # Convert BOM → UTF-8
    convert_to_utf8(file)

    # Read CSV with schema overrides
    df = pl.read_csv(
        file,
        encoding="utf8",
        schema_overrides={
            "機器・工事No": pl.Utf8,
            "工事ID": pl.Utf8,
            "作業ID": pl.Utf8,
            "進捗": pl.Utf8,
            "実績": pl.Utf8,
        }
    )

    # Add calendar columns
    df = add_calendar_columns(df, start_date, end_date)

    # Save as UTF-8
    df.write_csv(file, include_header=True)

    # Convert back to UTF-8-SIG
    convert_to_utf8_sig(file)


# ==============================================================================
# Main Processing
# ==============================================================================

def main():
    base_dir = Path.cwd()
    edit_dir = base_dir.parent / "Edit_folder"
    target_dir = edit_dir / "plant_information_sheet"

    period_file = edit_dir / "calendar_period.json"

    # Load calendar period
    try:
        start_date, end_date = load_period(period_file)
    except Exception as e:
        print(f"ERROR: {e}")
        return

    print(f"カレンダー期間：{start_date} ～ {end_date}")

    if not target_dir.exists():
        print("ERROR: plant_information_sheet フォルダが存在しません。")
        return

    # Process all CSV files
    for file in target_dir.glob("*.csv"):
        process_csv_file(file, start_date, end_date)

    print("INFO: plant_information_sheet 内の CSV にカレンダー列を追加しました。")


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    main()
