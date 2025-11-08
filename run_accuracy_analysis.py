# run_accuracy_analysis.py
import os
import pandas as pd
import numpy as np
from atproto import Client
from dotenv import load_dotenv
import time

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')
BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

# 採点済みのCSVファイル
CSV_FILE = 'analysis_for_checking_01.csv'
# ◀◀◀ 【変更】集計結果を保存するファイル (日本語版)
SUMMARY_FILE = 'accuracy_summary_for_excel_jp.txt'


def get_metadata_for_posts(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameを受け取り、post_uriを使ってBlueskyからメタデータを取得し、
    新しい列（followers_count, follows_count）を追加して返す。
    """
    print(f"Bluesky ({BSKY_HANDLE}) にログインしています...")
    try:
        client = Client()
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
    except Exception as e:
        print(f"ログインに失敗しました: {e}")
        return df

    uris = df['post_uri'].unique().tolist()
    print(f"{len(uris)} 件のユニークな投稿URIのメタデータを取得します...")

    # URIをキーとし、(followers, follows) を値とする辞書を作成
    metadata_map = {}
    
    # get_postsは最大25件まで
    for i in range(0, len(uris), 25):
        chunk_uris = uris[i:i+25]
        print(f"  {i+1}〜{i+len(chunk_uris)} 件目の投稿情報を取得中...")
        try:
            posts_response = client.app.bsky.feed.get_posts(
                params={'uris': chunk_uris}
            )
            for post in posts_response.posts:
                # 取得した投稿のメタデータを辞書に保存
                metadata_map[post.uri] = {
                    'followers_count': post.author.followers_count or 0,
                    'follows_count': post.author.follows_count or 0
                }
            time.sleep(0.1) # サーバー負荷軽減
        except Exception as e:
            print(f"    URIチャンクの取得中にエラーが発生しました: {e}")

    # 辞書のマッピングを使って新しい列を効率的に作成
    df['followers_count'] = df['post_uri'].map(
        lambda uri: metadata_map.get(uri, {}).get('followers_count')
    )
    df['follows_count'] = df['post_uri'].map(
        lambda uri: metadata_map.get(uri, {}).get('follows_count')
    )

    # 取得できなかった行（削除された投稿など）は 0 で埋める
    df['followers_count'] = df['followers_count'].fillna(0).astype(int)
    df['follows_count'] = df['follows_count'].fillna(0).astype(int)
    
    print("メタデータの取得とマージが完了しました。")
    return df

def analyze_binned_accuracy(df: pd.DataFrame, metric: str, bins: list, labels: list, output_file):
    """
    指定されたメトリック（列名）とビン（区間）に基づいて、
    3つの分類軸の正解率（平均）と件数を計算して表示し、
    結果をテキストファイルにも書き出す。
    
    ◀◀◀ 【変更】タイトルと列名を日本語化 ▼▼▼
    """
    
    # 英語のメトリック名を日本語のタイトルにマッピング
    METRIC_MAP = {
        'followers_count': 'フォロワー数',
        'follows_count': 'フォロー数',
        'text_length': '投稿の文字数'
    }
    
    analysis_title = f"【分析】{METRIC_MAP.get(metric, metric)} 別 の分類精度"
    separator = "="*50
    
    print("\n" + separator)
    print(analysis_title)
    print(separator)
    
    output_file.write(f"\n{separator}\n")
    output_file.write(f"{analysis_title}\n")
    output_file.write(f"{separator}\n")
    
    # 'post_text' 列から text_length を計算 (metric が 'text_length' の場合)
    if metric == 'text_length' and 'text_length' not in df.columns:
        # post_text が NaN (空) の場合を考慮
        df['text_length'] = df['post_text'].fillna('').str.len()

    # NaNやInfを0に置き換えてからbinning
    df[metric] = pd.to_numeric(df[metric], errors='coerce').fillna(0)
    
    # pd.cut を使ってデータをビン（グループ）に分ける
    df[f'{metric}_bin'] = pd.cut(df[metric], bins=bins, labels=labels, right=False)
    
    # ビンごとにグループ化し、各精度の平均（＝正解率）と件数を計算
    accuracy_columns = [
        'is_content_correct (0 or 1)',
        'is_expression_correct (0 or 1)',
        'is_style_correct (0 or 1)'
    ]
    
    # ◀◀◀ 【変更】列名を日本語に定義
    JP_COLS_ACC = {
        'is_content_correct (0 or 1)': 'コンテンツ正解率',
        'is_expression_correct (0 or 1)': '表現(感情)正解率',
        'is_style_correct (0 or 1)': 'スタイル正解率'
    }
    JP_COLS_COUNT = {
        'is_content_correct (0 or 1)': 'コンテンツ件数',
        'is_expression_correct (0 or 1)': '表現(感情)件数',
        'is_style_correct (0 or 1)': 'スタイル件数'
    }

    # .mean() を .apply('mean') に変更し、日本語列名を適用
    binned_stats_mean = df.groupby(f'{metric}_bin', observed=True)[accuracy_columns].apply('mean').rename(columns=JP_COLS_ACC)
    
    # .count() を .apply('count') に変更し、日本語列名を適用
    binned_stats_count = df.groupby(f'{metric}_bin', observed=True)[accuracy_columns].apply('count').rename(columns=JP_COLS_COUNT)
    
    # 結合して表示
    final_stats = pd.concat([binned_stats_mean, binned_stats_count], axis=1)
    
    # ◀◀◀ 【変更】インデックス名を日本語に
    final_stats.index.name = f"{METRIC_MAP.get(metric, metric)}_グループ"
    
    # 見やすいように調整 (コンソール出力用)
    pd.set_option('display.float_format', '{:.2%}'.format) # %表示
    print(final_stats)
    pd.reset_option('display.float_format') # 設定をリセット
    
    # Excelにコピペしやすい形式 (タブ区切り) でファイルに書き出す
    final_stats_percent = final_stats.copy()
    
    # ◀◀◀ 【変更】日本語の列名リストを使って%表示に変換
    acc_cols_jp = JP_COLS_ACC.values()
    for col in acc_cols_jp:
        if col in final_stats_percent.columns:
            final_stats_percent[col] = final_stats_percent[col].apply(lambda x: f"{x:.2%}")
            
    final_stats_percent.to_csv(output_file, sep='\t')


def main():
    try:
        # 1. 採点済みCSVを読み込む
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"エラー: {CSV_FILE} が見つかりません。")
        print("先に export_timeline_for_analysis.py を実行し、")
        print("次に check_tool.py で採点を完了させてください。")
        return

    # 採点が完了しているかチェック
    if df['is_content_correct (0 or 1)'].isna().any():
        print("警告: まだ採点が完了していない行があります。")
        print("（採点済みのデータのみで分析を続行します）")
        df = df.dropna(subset=['is_content_correct (0 or 1)'])
        if df.empty:
            print("分析できる採点済みデータがありません。")
            return
            
    # 2. メタデータをBlueskyから取得してDFにマージ
    df = get_metadata_for_posts(df)

    # 3. 集計結果を保存するファイルを開く
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        print(f"\n集計結果を {SUMMARY_FILE} に書き出します...")
        
        # フォロワー数のビン
        follower_bins = [0, 100, 500, 2000, 10000, np.inf]
        follower_labels = ['0-99', '100-499', '500-1999', '2000-9999', '10000+']
        analyze_binned_accuracy(df, 'followers_count', follower_bins, follower_labels, f) # ◀ 英語のmetric名で呼び出す

        # フォロー数のビン
        follow_bins = [0, 100, 500, 2000, np.inf]
        follow_labels = ['0-99', '100-499', '500-1999', '2000+']
        analyze_binned_accuracy(df, 'follows_count', follow_bins, follow_labels, f) # ◀ 英語のmetric名で呼び出す

        # 文章の長さのビン
        length_bins = [0, 50, 100, 150, 200, np.inf]
        length_labels = ['0-49', '50-99', '100-149', '150-199', '200+']
        analyze_binned_accuracy(df, 'text_length', length_bins, length_labels, f) # ◀ 英語のmetric名で呼び出す

    print(f"\n✅ 集計サマリーを {SUMMARY_FILE} に保存しました。")
    print("このファイルをメモ帳などで開き、内容をExcelにコピー＆ペーストしてグラフを作成してください。")


if __name__ == "__main__":
    main()