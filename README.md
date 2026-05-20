Stage3 の構成
1. PreprocessingModule（前処理：補修名称置換・クリーニング）
補修①〜⑩ → 補修1〜10 の名称正規化

改行除去・指数表記対策

進捗情報・履歴情報のクリーニング

後続処理で利用する「作業＆機器工事ID」列の生成

repair_name_replace.py

2. CsvExporter（Excel → CSV 展開）
GUI で対象期間を選択

Excel の全シートを CSV 化

プラント名 × 機器名称 × 会社名 を組み合わせた「名称」ごとの CSV を生成

plant_information_sheet フォルダへ自動仕分け

main_csv.py

3. CalendarColumnAdder（カレンダー列追加）
calendar_period.json を読み込み

Polars により高速に日付列（YYYY-MM-DD）を追加

plant_information_sheet 内の全 CSV に対して一括処理

calendar_columns.py

4. TaskTimelineMapper（作業名の期間展開）
進捗履歴情報から Min/Max 日付を算出

計画・実績・履歴の 6 種類の日付から最小・最大を決定

NumPy による高速マスク処理で、作業名を Min〜Max の範囲に配置

作業担当名 → 機器・工事No の順でソート

