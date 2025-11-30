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
# 集計結果を保存するファイル (日本語版)
SUMMARY_FILE = 'accuracy_summary_for_excel_jp.txt'


def get_metadata_for_posts(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameを受け取り、post_uriを使ってBlueskyからメタデータを取得し、
    新しい列（followers_count, follows_count）を追加して返す。（APIエラー対応済み）
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
            
            # 投稿ごとにループ
            for post in posts_response.posts:
                author_did = post.author.did
                
                # 個別プロファイル取得で統計情報を補完 (APIエラー対策)
                followers_count = 0
                follows_count = 0
                
                try:
                    # get_profileは ProfileViewDetailed を返す（統計情報を含む）
                    full_profile = client.get_profile(author_did) 
                    
                    # Noneチェックを行い、0でフォールバック
                    followers_count = full_profile.followers_count if full_profile.followers_count is not None else 0
                    follows_count = full_profile.follows_count if full_profile.follows_count is not None else 0
                    
                except Exception:
                    # プロファイル取得に失敗した場合（アカウント削除など）
                    pass
                    
                # 取得した投稿のメタデータを辞書に保存
                metadata_map[post.uri] = {
                    'followers_count': followers_count,
                    'follows_count': follows_count
                }

            time.sleep(0.1) # サーバー負荷軽減
        except Exception as e:
            # このチャンク全体の取得に失敗した場合（例: post_uriが無効など）
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


def calculate_and_display_stats(df: pd.DataFrame, group_col: str, title: str, output_file):
    """
    指定された列でグループ化して、正解率と件数を計算し、
    MarkdownテーブルとCSVをファイルに出力する。
    """
    
    METRIC_MAP = {
        'followers_count_group': 'フォロワー数',
        'follows_count_group': 'フォロー数',
        'text_length_group': '投稿の文字数',
    }
    
    # 総合結果の場合、グループ化は行全体
    if group_col == 'overall':
        # 行全体で平均とカウントを計算し、ダミーのグループを作成
        stats_mean = df[['is_content_correct (0 or 1)', 'is_expression_correct (0 or 1)', 'is_style_correct (0 or 1)']].apply('mean').to_frame().T
        stats_count = df[['is_content_correct (0 or 1)', 'is_expression_correct (0 or 1)', 'is_style_correct (0 or 1)']].apply('count').to_frame().T
        stats_mean.index = [title]
        stats_count.index = [title]
        stats_mean.index.name = '集計グループ'
    else:
        # グループ化して平均とカウントを計算
        stats_mean = df.groupby(group_col, observed=True)[['is_content_correct (0 or 1)', 'is_expression_correct (0 or 1)', 'is_style_correct (0 or 1)']].apply('mean')
        stats_count = df.groupby(group_col, observed=True)[['is_content_correct (0 or 1)', 'is_expression_correct (0 or 1)', 'is_style_correct (0 or 1)']].apply('count')
        stats_mean.index.name = METRIC_MAP.get(group_col, group_col) + '_グループ'


    # 日本語列名に変換するための辞書
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

    # 列名変更
    stats_mean = stats_mean.rename(columns=JP_COLS_ACC)
    stats_count = stats_count.rename(columns=JP_COLS_COUNT)

    # 結合
    final_stats = pd.concat([stats_mean, stats_count], axis=1)

    # タイトルをファイルに書き出し
    separator = "="*50
    output_file.write(f"\n{separator}\n")
    output_file.write(f"【分析】{title}\n")
    output_file.write(f"{separator}\n")

    # Markdown形式で表示 (正解率はパーセント表記)
    display_stats = final_stats.copy()
    for col in JP_COLS_ACC.values():
        display_stats[col] = display_stats[col].apply(lambda x: f"{x:.2%}")

    # コンソールにはMarkdownテーブルで表示
    print(f"\n【分析】{title}")
    print(display_stats.to_markdown(numalign="left", stralign="left"))
    
    # Excelにコピペしやすい形式 (タブ区切り) でファイルに書き出す
    final_stats_excel = final_stats.copy()
    for col in JP_COLS_ACC.values():
        # 小数点以下4桁の固定形式で出力（Excelで数値として処理しやすくするため）
        final_stats_excel[col] = final_stats_excel[col].apply(lambda x: f"{x:.4f}") 
            
    final_stats_excel.to_csv(output_file, sep='\t', float_format='%.4f')


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
        # NaNではない行のみを抽出
        df = df.dropna(subset=['is_content_correct (0 or 1)'])
        if df.empty:
            print("分析できる採点済みデータがありません。")
            return
            
    # 2. メタデータをBlueskyから取得してDFにマージ
    df = get_metadata_for_posts(df)

    # 3. 事前処理: text_lengthを計算
    if 'text_length' not in df.columns:
        # post_text が NaN (空) の場合を考慮して文字数（長さ）を計算
        df['text_length'] = df['post_text'].fillna('').str.len()
    
    # 4. 集計結果を保存するファイルを開く
    with open(SUMMARY_FILE, 'w', encoding='utf-8') as f:
        print(f"\n集計結果を {SUMMARY_FILE} に書き出します...")
        
        # 4-1. 総合結果の表示
        calculate_and_display_stats(df, 'overall', '総合分類精度 (全件)', f)

        # 4-2. 固定ビンによるグループ分析（常に固定ビンを使用）
        
        # フォロワー数
        followers = df['followers_count']
        follower_bins = [0, 100, 500, 2000, 10000, np.inf]
        follower_labels = ['0-99', '100-499', '500-1999', '2000-9999', '10000+']
        # right=Falseで [0, 100) のように境界値を含まないように設定
        df['followers_count_group'] = pd.cut(followers, bins=follower_bins, labels=follower_labels, right=False)

        calculate_and_display_stats(df, 'followers_count_group', 'フォロワー数別 (固定ビン)', f)

        # フォロー数
        follows = df['follows_count']
        follow_bins = [0, 100, 500, 2000, np.inf]
        follow_labels = ['0-99', '100-499', '500-1999', '2000+']
        df['follows_count_group'] = pd.cut(follows, bins=follow_bins, labels=follow_labels, right=False)

        calculate_and_display_stats(df, 'follows_count_group', 'フォロー数別 (固定ビン)', f)

        # 投稿の文字数
        text_length = df['text_length']
        length_bins = [0, 50, 100, 150, 200, np.inf]
        length_labels = ['0-49', '50-99', '100-149', '150-199', '200+']
        df['text_length_group'] = pd.cut(text_length, bins=length_bins, labels=length_labels, right=False)
            
        calculate_and_display_stats(df, 'text_length_group', '投稿の文字数別 (固定ビン)', f)


    print(f"\n✅ 集計サマリーを {SUMMARY_FILE} に保存しました。")
    print("このファイルをメモ帳などで開き、内容をExcelにコピー＆ペーストしてグラフを作成してください。")


if __name__ == "__main__":
    main()