"""
Stage3 Task Mapping Processor
-----------------------------

This module performs the following operations:

1. Load progress history (進捗履歴情報.csv).
2. Compute Min/Max dates per 作業＆機器工事ID.
3. For each CSV in plant_information_sheet:
    - Clean date columns
    - Compute Min/Max across 6 date sources
    - Place 作業名 across Min_col〜Max_col range
    - Sort rows by 作業担当名 → 機器・工事No
4. Save updated CSV files (UTF-8-SIG)

This script is intended to be used as part of the Stage3 pipeline
in the Data Preprocessing Pipeline project.

Author: YOUR_NAME
Repository: https://github.com/yourname/yourrepo
"""

from pathlib import Path
import pandas as pd
import numpy as np
import re
import os


# ==============================================================================
# Utility Functions
# ==============================================================================

def clean_date(value) -> str | None:
    """
    Normalize date strings into a consistent format.

    Parameters
    ----------
    value : Any
        Raw date value.

    Returns
    -------
    str | None
        Cleaned date string or None.
    """
    if pd.isna(value):
        return None

    s = str(value).strip()
    s = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?$", "", s)  # remove time
    s = re.sub(r"年|月", "/", s)
    s = s.replace("日", "")
    s = s.replace("-", "/")
    return s


def is_date_like(col_name: str) -> bool:
    """
    Determine whether a column name represents a date.

    Parameters
    ----------
    col_name : str

    Returns
    -------
    bool
    """
    if not isinstance(col_name, str):
        return False

    s = col_name.strip().replace("\ufeff", "")

    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", s):
        return True

    try:
        pd.to_datetime(s, errors="raise")
        return True
    except Exception:
        return False


# ==============================================================================
# History Processing
# ==============================================================================

def load_history(edit_dir: Path) -> tuple[pd.Series, pd.Series]:
    """
    Load progress history and compute Min/Max per 作業＆機器工事ID.

    Returns
    -------
    (hist_min, hist_max)
    """
    history_file = edit_dir / "進捗履歴情報.csv"

    if not history_file.exists():
        raise FileNotFoundError("進捗履歴情報.csv が見つかりません")

    df_hist = pd.read_csv(history_file)

    required = {"作業＆機器工事ID", "日付"}
    if not required.issubset(df_hist.columns):
        raise ValueError("進捗履歴情報.csv に必要な列がありません")

    df_hist["日付"] = pd.to_datetime(df_hist["日付"].apply(clean_date), errors="coerce")

    hist_min = df_hist.groupby("作業＆機器工事ID")["日付"].min()
    hist_max = df_hist.groupby("作業＆機器工事ID")["日付"].max()

    return hist_min, hist_max


# ==============================================================================
# File Processing
# ==============================================================================

def process_csv_file(file: Path,
                     hist_min: pd.Series,
                     hist_max: pd.Series) -> None:
    """
    Process a single CSV file inside plant_information_sheet.

    Parameters
    ----------
    file : Path
        CSV file path.
    hist_min : pd.Series
        Min date per 作業＆機器工事ID.
    hist_max : pd.Series
        Max date per 作業＆機器工事ID.
    """
    df = pd.read_csv(file)

    if "作業名" not in df.columns:
        print(f"{file.name}: 作業名が無いためスキップ")
        return

    # Identify start/end columns
    start_candidates = ["計画開始日", "実績開始日"]
    end_candidates = ["計画終了日", "実績終了日"]

    start_col = next((c for c in start_candidates if c in df.columns), None)
    end_col = next((c for c in end_candidates if c in df.columns), None)

    if not start_col or not end_col:
        print(f"{file.name}: 開始日／終了日が無いためスキップ")
        return

    # Identify calendar columns
    date_cols = [col for col in df.columns if is_date_like(col)]
    if not date_cols:
        print(f"{file.name}: 日付列が無いためスキップ")
        return

    col_dates = pd.to_datetime(date_cols).normalize()

    # Clean start/end dates
    df["start_dt"] = pd.to_datetime(df[start_col].apply(clean_date), errors="coerce").dt.normalize()
    df["end_dt"] = pd.to_datetime(df[end_col].apply(clean_date), errors="coerce").dt.normalize()
    df["end_dt"] = df["end_dt"].fillna(df["start_dt"])

    # Add history Min/Max
    if "作業＆機器工事ID" in df.columns:
        df["進捗_Min_col"] = df["作業＆機器工事ID"].map(hist_min).dt.strftime("%Y/%m/%d")
        df["進捗_Max_col"] = df["作業＆機器工事ID"].map(hist_max).dt.strftime("%Y/%m/%d")
    else:
        df["進捗_Min_col"] = ""
        df["進捗_Max_col"] = ""

    # Compute Min/Max across 6 sources
    date_sources = [
        "実績開始日",
        "実績終了日",
        "start_dt",
        "end_dt",
        "進捗_Min_col",
        "進捗_Max_col",
    ]

    existing_sources = [c for c in date_sources if c in df.columns]

    tmp_dates = df[existing_sources].apply(
        lambda row: pd.to_datetime(row.apply(clean_date), errors="coerce"),
        axis=1
    )

    df["Min_col"] = tmp_dates.min(axis=1).dt.normalize()
    df["Max_col"] = tmp_dates.max(axis=1).dt.normalize()

    # Place 作業名 across Min〜Max
    min_matrix = df["Min_col"].values[:, None] <= col_dates.values
    max_matrix = df["Max_col"].values[:, None] >= col_dates.values
    mask = min_matrix & max_matrix

    df[date_cols] = np.where(mask, df["作業名"].values[:, None], "")

    # Sort
    sort_keys = [c for c in ["作業担当名", "機器・工事No"] if c in df.columns]
    if sort_keys:
        df = df.sort_values(by=sort_keys, ascending=True, na_position="last")

    df.to_csv(file, index=False, encoding="utf-8-sig")


# ==============================================================================
# Main
# ==============================================================================

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    base_dir = Path.cwd()
    edit_dir = base_dir.parent / "Edit_folder"
    target_dir = edit_dir / "plant_information_sheet"

    if not target_dir.exists():
        print("plant_information_sheet フォルダが存在しません。")
        return

    print("高速版：作業名配置＋Min/Max処理＋ソートを実行中…")

    # Load history
    try:
        hist_min, hist_max = load_history(edit_dir)
    except Exception as e:
        print(f"ERROR: {e}")
        return

    # Process each CSV
    for file in target_dir.glob("*.csv"):
        process_csv_file(file, hist_min, hist_max)

    print("処理が完了しました。")


if __name__ == "__main__":
    main()
