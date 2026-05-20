Stage3 は以下の 4 ステップで構成されています：

1. Excel → CSV 展開（main_csv.py）
GUI で対象期間を選択

Excel の全シートを CSV 化

プラント名・機器名称・会社名を組み合わせた「名称」ごとの CSV を生成

plant_information_sheet フォルダへ自動仕分け

2. カレンダー列の追加（calendar_columns.py）
calendar_period.json を読み込み

Polars により高速に日付列（YYYY-MM-DD）を追加

全 CSV に対して日付列を一括付与

3. 作業名の期間展開（task_mapping.py）
進捗履歴情報から Min/Max 日付を算出

計画・実績・履歴の 6 種類の日付から最小・最大を決定

Min〜Max の範囲に作業名を配置（NumPy による高速処理）

4. 補助処理（repair_name_replace.py）
補修①〜⑩ の名称を補修1〜10 に正規化

改行除去・指数表記対策などの前処理

📂 Directory Structure
コード
repository/
├── main_csv.py                 # Excel → CSV 展開
├── calendar_columns.py         # カレンダー列追加
├── task_mapping.py             # 作業名の期間展開
├── repair_name_replace.py      # 補修名称置換・前処理
├── Edit_folder/                # 自動生成フォルダ
│   ├── calendar_period.json
│   └── plant_information_sheet/
│       └── *.csv
└── README.md
🚀 Usage
1. Step1: Excel → CSV 展開
コード
python main_csv.py
GUI が表示されるので、対象期間を選択します。

2. Step2: カレンダー列追加
コード
python calendar_columns.py
3. Step3: 作業名の期間展開
コード
python task_mapping.py
4. Step4: 補修名称置換（必要に応じて）
コード
python repair_name_replace.py
⚙️ Requirements
Python 3.10+

pandas

numpy

polars

PySide6

openpyxl

コード
pip install pandas numpy polars PySide6 openpyxl
🧠 Background
本パイプラインは、数百万〜数千万レコード規模の進捗データを扱う業務システム向けに設計されています。

Excel では扱いきれないデータ量を CSV に分割

Polars による高速処理

NumPy による日付範囲マッピング

GUI による期間選択

後続の Excel 集約・BI ツールでの可視化に最適化

📄 License
