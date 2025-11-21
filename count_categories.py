import pandas as pd
import numpy as np

# 採点対象のCSVファイルをフルパスで指定
CSV_FILE = 'analysis_for_checking_01.csv'

def calculate_category_distribution(df: pd.DataFrame):
    """コンテンツ、感情、スタイルカテゴリの件数（分布）を計算し、表示する。"""
    
    JP_COLS = {
        'llm_content_category': 'コンテンツカテゴリ',
        'llm_expression_category': '表現(感情)カテゴリ',
        'llm_style_stance_category': 'スタイルカテゴリ'
    }

    print("==========================================")
    print("【分析】カテゴリ別件数（分布）")
    print("==========================================")
    
    for llm_col, jp_col in JP_COLS.items():
        if llm_col in df.columns:
            # カテゴリ名で集計し、件数が多い順にソート
            counts = df[llm_col].value_counts().to_frame(name='件数')
            counts.index.name = jp_col
            
            print(f"\n--- {jp_col} ---")
            print(counts.to_string())
        else:
            print(f"警告: 列 '{llm_col}' が見つかりませんでした。")

def calculate_text_length_distribution(df: pd.DataFrame):
    """
    投稿の文字数分布を計算し、表示する。
    1〜300文字までを6分類（50文字刻みの固定ビン）で均等に分割する。
    """
    
    if 'post_text' not in df.columns:
        print("\n警告: 'post_text' 列が見つかりませんでした。文字数分布を計算できません。")
        return

    # 1. 文字数を計算
    df['text_length'] = df['post_text'].fillna('').str.len().astype(int)
    
    # 2. 0文字の投稿を除外
    data_for_analysis = df[df['text_length'] > 0].copy()

    if data_for_analysis.empty:
        print("\n有効なテキスト投稿が見つかりませんでした。")
        return

    print("\n==========================================")
    print("【分析】投稿の文字数別 件数（1-300字を6分類）")
    print("==========================================")

    # 3. 1〜300文字までを50文字刻みの固定ビンで定義
    # binの境界: (0, 50], (50, 100], ..., (250, 300], (300, inf]
    bins = [0, 50, 100, 150, 200, 250, 300, np.inf]
    labels = ['1-50字', '51-100字', '101-150字', '151-200字', '201-250字', '251-300字', '300字超']

    try:
        # pd.cut を使用し、right=True（右側を含める）設定で、1文字が最初のビンに入るようにする
        data_for_analysis['text_length_group_fixed'] = pd.cut(
            data_for_analysis['text_length'], 
            bins=bins, 
            labels=labels, 
            right=True, 
            include_lowest=True
        )
        
        # グループごとの件数を計算し、ラベル順にソートして出力
        counts = data_for_analysis['text_length_group_fixed'].value_counts(dropna=False).to_frame(name='件数')
        counts.index.name = '文字数グループ (固定ビン)'
        
        # ラベルのソート順（categories）で並べ替える
        counts = counts.reindex(labels) 
        
        print(counts.to_string())

    except Exception as e:
        print(f"警告: 文字数でのグループ分け中に予期せぬエラーが発生しました: {e}")

def main():
    try:
        # 1. 採点済みCSVを読み込む
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"エラー: {CSV_FILE} が見つかりませんでした。")
        return
    except Exception as e:
        print(f"エラー: ファイルの読み込み中にエラーが発生しました: {e}")
        return

    # 2. カテゴリ別の分布を計算・表示
    calculate_category_distribution(df)

    # 3. 投稿の文字数分布を計算・表示
    calculate_text_length_distribution(df)

if __name__ == "__main__":
    main()