import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# ファイルパス設定
CSV_FILE = 'analysis_for_checking_01.csv'

def main():
    if not os.path.exists(CSV_FILE):
        print(f"エラー: {CSV_FILE} が見つかりません。")
        return

    # 1. データを読み込む
    print("データを読み込んでいます...")
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    
    # 採点済み（コンテンツ正解率が空でない）データのみを抽出
    df = df.dropna(subset=['is_content_correct (0 or 1)']).copy()

    if df.empty:
        print("採点済みのデータがありません。")
        return

    # 2. データ前処理（抽出と計算）
    # フォロワー数
    df['followers_count'] = df['post_text'].str.extract(
        r'^\s*投稿 \d+\s*】\s*著者: @.+?\s*統計: (\d+) フォロワー', expand=False
    ).fillna(0).astype(float)
    
    # フォロー数
    df['follows_count'] = df['post_text'].str.extract(
        r'/\s*(\d+) フォロー\s*文字:', expand=False
    ).fillna(0).astype(float)
    
    # 投稿の文字数
    df['text_length'] = df['post_text'].fillna('').str.len().astype(float)

    # 3. 固定ビンの定義
    # フォロワー数グループ
    follower_bins = [0, 100, 500, 2000, 10000, np.inf]
    follower_labels = ['0-99', '100-499', '500-1999', '2000-9999', '10000+']
    df['follower_group'] = pd.cut(df['followers_count'], bins=follower_bins, labels=follower_labels, right=False)

    # フォロー数グループ
    follow_bins = [0, 100, 500, 2000, np.inf]
    follow_labels = ['0-99', '100-499', '500-1999', '2000+']
    df['follow_group'] = pd.cut(df['follows_count'], bins=follow_bins, labels=follow_labels, right=False)

    # 文字数グループ
    length_bins = [0, 50, 100, 150, 200, np.inf]
    length_labels = ['0-49', '50-99', '100-149', '150-199', '200+']
    df['length_group'] = pd.cut(df['text_length'], bins=length_bins, labels=length_labels, right=False)

    # 4. グラフの作成と保存
    # 正解率のカラム定義
    accuracy_cols = {
        'is_content_correct (0 or 1)': 'Content',     # コンテンツ
        'is_expression_correct (0 or 1)': 'Expression', # 表現(感情)
        'is_style_correct (0 or 1)': 'Style'          # スタイル
    }

    # 日本語フォントの設定が環境によって難しいため、英語ラベルを使用します
    plot_accuracy(df, 'follower_group', accuracy_cols, 
                 'Accuracy by Followers Count (Fixed Bins)', 'accuracy_by_followers.png')
    
    plot_accuracy(df, 'follow_group', accuracy_cols, 
                 'Accuracy by Follows Count (Fixed Bins)', 'accuracy_by_follows.png')
    
    plot_accuracy(df, 'length_group', accuracy_cols, 
                 'Accuracy by Text Length (Fixed Bins)', 'accuracy_by_length.png')

def plot_accuracy(df, group_col, accuracy_cols, title, filename):
    # グループごとの平均を計算
    grouped = df.groupby(group_col, observed=True)[list(accuracy_cols.keys())].mean()
    grouped.columns = [accuracy_cols[c] for c in grouped.columns]
    
    # グラフ描画
    plt.figure(figsize=(10, 6))
    ax = grouped.plot(kind='bar', width=0.8)
    
    plt.title(title)
    plt.ylabel('Accuracy') # 正解率
    plt.xlabel(group_col.replace('_group', '').replace('_', ' ').title())
    plt.ylim(0, 1.1) # Y軸の範囲 (0%〜110%程度)
    plt.legend(loc='lower right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=0) # X軸ラベルを横向きに
    
    # バーの上に数値を表示
    for p in ax.patches:
        val = p.get_height()
        if val > 0: # 0より大きい場合のみ表示
            ax.annotate(f"{val:.2f}", (p.get_x() + p.get_width() / 2., val),
                        ha='center', va='bottom', xytext=(0, 3), textcoords='offset points')
    
    plt.tight_layout()
    plt.savefig(filename)
    print(f"グラフを保存しました: {filename}")
    plt.close()

if __name__ == "__main__":
    main()