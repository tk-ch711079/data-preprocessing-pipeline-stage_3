"""
Stage3 CSV Exporter
-------------------

This module performs the following operations:

1. GUI-based date range selection.
2. Load the latest Excel file from the input directory.
3. Export all Excel sheets as CSV.
4. Generate intermediate CSV files (途中①〜③).
5. Create plant-specific CSV files based on normalized names.
6. Move categorized CSV files into a dedicated folder.

This script is intended to be used as part of the Stage3 pipeline
in the Data Preprocessing Pipeline project.

Author: YOUR_NAME
Repository: https://github.com/yourname/yourrepo
"""

from pathlib import Path
from datetime import datetime, timedelta
import json
import shutil
import sys
import re
import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QDateEdit, QMessageBox
)
from PySide6.QtCore import QDate


# ==============================================================================
# Utility Functions
# ==============================================================================

def safe_sheet_name(name: str) -> str:
    """
    Convert a string into a safe Excel sheet name (max 31 chars).

    Parameters
    ----------
    name : str
        Original sheet name.

    Returns
    -------
    str
        Sanitized sheet name.
    """
    name = str(name)
    name = re.sub(r'[\/\\\*\?

\[\]

]', ' ', name)
    name = name.strip()
    return name[:31]


def ensure_directory(path: Path) -> None:
    """Create directory if it does not exist."""
    path.mkdir(exist_ok=True)


# ==============================================================================
# GUI: Date Range Selector
# ==============================================================================

def get_date_range_gui(edit_dir: Path):
    """
    Display a GUI to select a date range.

    Parameters
    ----------
    edit_dir : Path
        Directory to save selected period JSON.

    Returns
    -------
    tuple[date, date]
        (start_date, end_date)
    """
    today = datetime.today().date()

    app = QApplication.instance() or QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("対象期間の選択")
    window.resize(480, 260)

    notice = QLabel("※開始日と終了日を自由に選択できます。")

    start_label = QLabel("開始日")
    end_label = QLabel("終了日")

    start_cal = QDateEdit()
    start_cal.setCalendarPopup(True)
    start_cal.setDate(QDate(today.year, today.month, today.day))

    default_end = today + timedelta(days=30)
    end_cal = QDateEdit()
    end_cal.setCalendarPopup(True)
    end_cal.setDate(QDate(default_end.year, default_end.month, default_end.day))

    def submit():
        start = start_cal.date().toPython()
        end = end_cal.date().toPython()

        if start > end:
            QMessageBox.critical(window, "エラー", "開始日は終了日より前にしてください。")
            return

        window.start_date = start
        window.end_date = end

        period_file = edit_dir / "calendar_period.json"
        with period_file.open("w", encoding="utf-8") as f:
            json.dump(
                {"start": start.strftime("%Y-%m-%d"),
                 "end": end.strftime("%Y-%m-%d")},
                f, ensure_ascii=False, indent=2
            )

        window.close()

    button = QPushButton("決定")
    button.clicked.connect(submit)

    layout = QVBoxLayout()
    layout.addWidget(notice)

    hl1 = QHBoxLayout()
    hl1.addWidget(start_label)
    hl1.addWidget(start_cal)
    layout.addLayout(hl1)

    hl2 = QHBoxLayout()
    hl2.addWidget(end_label)
    hl2.addWidget(end_cal)
    layout.addLayout(hl2)

    layout.addWidget(button)
    window.setLayout(layout)

    window.show()
    app.exec()

    return getattr(window, "start_date", None), getattr(window, "end_date", None)


# ==============================================================================
# Excel / CSV Processing
# ==============================================================================

def load_latest_excel(input_dir: Path) -> tuple[pd.DataFrame, Path]:
    """Load the latest Excel file from input_dir."""
    if not input_dir.exists():
        raise FileNotFoundError("ERROR: 『ファイル設置場所』フォルダが存在しません。")

    files = sorted(input_dir.glob("*.xlsx"),
                   key=lambda f: f.stat().st_mtime,
                   reverse=True)

    if not files:
        raise FileNotFoundError("ERROR: .xlsx ファイルが見つかりません。")

    excel_path = files[0]
    xls = pd.ExcelFile(excel_path)

    if "進捗情報" not in xls.sheet_names:
        raise ValueError("ERROR: Excel に『進捗情報』シートがありません。")

    df = pd.read_excel(excel_path, sheet_name="進捗情報")
    return df, excel_path


def export_all_sheets_as_csv(excel_path: Path, output_dir: Path):
    """Export all sheets in an Excel file as CSV."""
    sheets = pd.read_excel(excel_path, sheet_name=None)

    for sheet_name, df_sheet in sheets.items():
        safe_name = safe_sheet_name(sheet_name)
        csv_path = output_dir / f"{safe_name}.csv"
        df_sheet.to_csv(csv_path, index=False, encoding="utf-8-sig")


def export_csv(df: pd.DataFrame, output_path: Path):
    """Export DataFrame to CSV."""
    df.to_csv(output_path, index=False, encoding="utf-8-sig")


# ==============================================================================
# Main Processing
# ==============================================================================

def generate_intermediate_files(df_raw: pd.DataFrame, edit_dir: Path):
    """Generate 途中①〜③ CSV files and plant-specific CSVs."""
    cols = ['プラント名', '機器・工事名称', '会社名']
    df_raw[cols] = df_raw[cols].fillna("").astype(str)

    df_name = (
        df_raw[cols]
        .drop_duplicates()
        .sort_values(by='プラント名')
        .reset_index(drop=True)
    )
    df_name.insert(0, 'No', df_name.index + 1)

    df_name['名称'] = (
        df_name['プラント名'] +
        df_name['機器・工事名称'] +
        df_name['会社名']
    ).apply(safe_sheet_name)

    export_csv(df_name, edit_dir / f"{safe_sheet_name('途中①')}.csv")

    # 途中②
    required = [
        '機器・工事名称', '作業担当名', '機器・工事No', '会社名',
        '進捗情報ID', 'プラント名', '機器・工事ID', '作業ID',
        '作業名', '進捗', '実績', '計画開始日',
        '計画終了日', '実績開始日', '実績終了日'
    ]

    missing = [c for c in required if c not in df_raw.columns]
    if missing:
        raise ValueError(f"必要な列が不足しています: {missing}")

    df_progress = df_raw[required].copy()

    df_progress = df_progress.merge(
        df_name[['プラント名', '機器・工事名称', '会社名', '名称']],
        on=['プラント名', '機器・工事名称', '会社名'],
        how='left'
    )

    df_progress['作業＆機器工事ID'] = (
        df_progress['作業ID'].astype(str) + "_" +
        df_progress['機器・工事ID'].astype(str)
    )

    export_csv(df_progress, edit_dir / f"{safe_sheet_name('途中②')}.csv")

    # 途中③（空ファイル）
    export_csv(pd.DataFrame(), edit_dir / f"{safe_sheet_name('途中③')}.csv")

    # 名称ごとの CSV 出力
    for name in df_name['名称'].unique():
        if not name:
            continue
        df_sub = df_progress[df_progress['名称'] == name]
        export_csv(df_sub, edit_dir / f"{name}.csv")


def move_plant_files(edit_dir: Path):
    """Move plant-specific CSV files into plant_information_sheet folder."""
    target_dir = edit_dir / "plant_information_sheet"
    ensure_directory(target_dir)

    exclude_files = {
        "カテゴリグループ.csv", "プラントグループ.csv", "会社情報.csv",
        "機器工事情報.csv", "作業情報.csv", "進捗情報.csv",
        "進捗履歴情報.csv", "不随情報.csv", "担当者.csv",
        "テスト系統.csv", "不随情報カラム用.csv", "法規.csv",
        "プラント_IDマスタ.csv",
        f"{safe_sheet_name('途中①')}.csv",
        f"{safe_sheet_name('途中②')}.csv",
        f"{safe_sheet_name('途中③')}.csv",
    }

    for file in edit_dir.glob("*.csv"):
        if file.name not in exclude_files:
            shutil.move(str(file), target_dir / file.name)

    # nan で始まるファイル削除
    for file in target_dir.glob("nan*.csv"):
        file.unlink()


# ==============================================================================
# Entry Point
# ==============================================================================

def main():
    base_dir = Path.cwd()
    input_dir = base_dir.parent / "ファイル設置場所"
    edit_dir = base_dir.parent / "Edit_folder"

    ensure_directory(edit_dir)

    start_date, end_date = get_date_range_gui(edit_dir)
    if not start_date or not end_date:
        raise ValueError("対象期間が選択されていません。")

    df_raw, excel_path = load_latest_excel(input_dir)

    export_all_sheets_as_csv(excel_path, edit_dir)
    export_csv(df_raw, edit_dir / "進捗情報.csv")

    generate_intermediate_files(df_raw, edit_dir)
    move_plant_files(edit_dir)

    print("INFO: Stage3 CSV Export completed.")


if __name__ == "__main__":
    main()
