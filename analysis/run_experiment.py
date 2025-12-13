import pandas as pd
import sys
import os
import time

# 親ディレクトリ（ルート）をパスに追加して app モジュールをインポートできるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app import llm_analyzer
except ImportError:
    print("【エラー】'app' モジュールが見つかりません。")
    print("このスクリプトは 'analysis' フォルダの中に配置し、")
    print("その一つ上の階層に 'app' フォルダがある状態で実行してください。")
    sys.exit(1)

# 入力ファイルと出力ファイルの設定
INPUT_CSV = 'analysis_for_checking_01.csv'
OUTPUT_CSV = 'analysis/experiment_result.csv' # 新しい分析結果

def main():
    # 1. データセットの読み込み
    csv_path = os.path.join(os.path.dirname(__file__), INPUT_CSV)
    if not os.path.exists(csv_path):
        # 実行ディレクトリ直下にある場合も考慮
        csv_path = INPUT_CSV
        
    if not os.path.exists(csv_path):
        print(f"エラー: {INPUT_CSV} が見つかりません。")
        return

    print(f"データセットを読み込んでいます: {INPUT_CSV}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    # 必要な列があるか確認
    if 'post_text' not in df.columns:
        print("エラー: CSVに 'post_text' 列がありません。")
        return

    # 分析対象のテキストリストを作成
    texts = df['post_text'].fillna("").tolist()
    uris = df['post_uri'].tolist()
    
    print(f"\n{len(texts)} 件の投稿に対し、LLM分析実験を開始します...")
    
    # 2. LLMによるバッチ分析実行
    # llm_analyzerの設定（APIキーなど）は llm_analyzer.py 内部で読み込まれます
    start_time = time.time()
    results = llm_analyzer.analyze_posts_batch(texts)
    end_time = time.time()
    
    print(f"分析完了 (所要時間: {end_time - start_time:.2f}秒)")

    # 3. 結果の集計と保存
    new_rows = []
    
    # 精度検証用のカウンター
    correct_count = 0
    total_checked = 0

    for i, (uri, text, res) in enumerate(zip(uris, texts, results)):
        old_row = df.iloc[i]
        
        # 新しい行データを作成
        new_row = {
            'post_uri': uri,
            'post_text': text,
            'new_content_category': res['content_category'],
            'new_expression_category': res['expression_category'],
            'new_style_category': res['style_stance_category'],
        }

        # --- 自動採点ロジック ---
        # 以前のデータで「正解(1.0)」がついている場合、その時のカテゴリを「正解ラベル」とみなして比較する
        
        # コンテンツ分類の検証
        is_match = False
        match_info = ""
        
        if 'is_content_correct (0 or 1)' in old_row and old_row['is_content_correct (0 or 1)'] == 1.0:
            total_checked += 1
            ground_truth = old_row['llm_content_category']
            
            if res['content_category'] == ground_truth:
                is_match = True
                correct_count += 1
                match_info = "〇 一致"
            else:
                match_info = f"× 不一致 (正解: {ground_truth})"
        else:
            match_info = "- (正解データなし)"

        new_row['accuracy_check'] = match_info
        new_rows.append(new_row)

    # DataFrame作成と保存
    result_df = pd.DataFrame(new_rows)
    output_path = os.path.join(os.path.dirname(__file__), 'experiment_result.csv')
    result_df.to_csv(output_path, index=False, encoding='utf-8-sig')

    # 4. 結果表示
    print("-" * 50)
    print(f"【実験結果サマリー】")
    print(f"データ総数: {len(texts)} 件")
    
    if total_checked > 0:
        accuracy = (correct_count / total_checked) * 100
        print(f"比較可能なデータ数 (過去に正解とされたもの): {total_checked} 件")
        print(f"今回の一致数: {correct_count} 件")
        print(f"再現率/正解率: {accuracy:.2f}%")
        print("\n※ 注意: この正解率は「過去の正解データと同じ分類ができたか」を示します。")
        print("   プロンプトを変更して「より良い分類」になった場合でも、過去の分類と異なれば「不一致」となります。")
    else:
        print("過去の正解データ(is_content_correct=1.0)が見つからなかったため、精度計算はスキップしました。")

    print(f"\n詳細な結果は {output_path} に保存されました。")
    print("-" * 50)

if __name__ == "__main__":
    main()