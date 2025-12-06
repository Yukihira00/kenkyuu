# export_timeline_for_analysis.py
import os
import csv
import time
import textwrap
import sys
from dotenv import load_dotenv
from atproto import Client
import app.llm_analyzer as llm_analyzer

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')

BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

# 出力ファイル名
CSV_FILE = "analysis_for_checking_01.csv"
TXT_FILE = "timeline_analysis_export.txt"

# --- ▼▼▼ 設定：文字数分布の目標値 ▼▼▼ ---
# 各ビンごとの目標収集件数
TARGET_COUNT_PER_BIN = 150

# 文字数の区切り（下限, 上限）
BINS = [
    (1, 50),
    (51, 100),
    (101, 150),
    (151, 200),
    (201, 250),
    (251, 300),
    (301, 10000) # 301文字以上
]
BIN_LABELS = [
    '1-50字', '51-100字', '101-150字', '151-200字', '201-250字', '251-300字', '300字超'
]

def get_bin_index(length):
    """文字数から該当するビンのインデックスを返す"""
    for i, (low, high) in enumerate(BINS):
        if low <= length <= high:
            return i
    return -1

def fetch_and_export_timeline():
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("エラー: .envファイルに BSKY_HANDLE と BSKY_APP_PASSWORD を設定してください。")
        return

    # 1. 既存データの読み込み（重複チェック & 文字数カウント用）
    existing_uris = set()
    existing_texts = set()
    
    # 各ビンの現在のデータ件数
    current_bin_counts = [0] * len(BINS)
    
    next_post_index = 1

    if os.path.exists(CSV_FILE):
        print(f"既存のファイル '{CSV_FILE}' を読み込んで分布を確認しています...")
        try:
            with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # URIとテキストの重複チェック用
                    existing_uris.add(row['post_uri'])
                    if 'post_text' in row:
                        text = row['post_text']
                        existing_texts.add(text)
                        
                        # 文字数をカウントしてビンに加算
                        length = len(text)
                        bin_idx = get_bin_index(length)
                        if bin_idx != -1:
                            current_bin_counts[bin_idx] += 1

            next_post_index = len(existing_uris) + 1
            print(f"  -> 既存データ合計: {len(existing_uris)}件")
        except Exception as e:
            print(f"  -> 警告: 既存ファイルの読み込みに失敗しました ({e})。新規作成として扱います。")

    # 現状の分布を表示
    print("\n【現在の収集状況】")
    all_bins_full = True
    for i, label in enumerate(BIN_LABELS):
        count = current_bin_counts[i]
        status = "✅ 完了" if count >= TARGET_COUNT_PER_BIN else f"あと {TARGET_COUNT_PER_BIN - count} 件"
        print(f"  {label:<10}: {count:>3} 件 ({status})")
        if count < TARGET_COUNT_PER_BIN:
            all_bins_full = False

    if all_bins_full:
        print("\nすべての文字数カテゴリで目標件数に達しています。新しい収集は不要です。")
        return

    # Blueskyクライアントを初期化・ログイン
    client = Client()
    try:
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
        print(f"\nBluesky ({BSKY_HANDLE}) にログインしました。")
    except Exception as e:
        print(f"Blueskyへのログインに失敗しました: {e}")
        return
    
    print(f"不足している文字数帯の投稿を検索します... (各目標 {TARGET_COUNT_PER_BIN} 件)")
    
    new_feed = [] # 採用した PostView
    cursor = None
    
    # 今回の実行で取得する最大件数（API負荷とLLMコストを考慮して安全装置をかける）
    MAX_NEW_POSTS_THIS_RUN = 50
    
    # 検索APIを回す最大回数（長い文章が見つからない場合の無限ループ防止）
    MAX_API_CALLS = 100 
    api_calls = 0
    
    try:
        while len(new_feed) < MAX_NEW_POSTS_THIS_RUN and api_calls < MAX_API_CALLS:
            # 進捗表示
            api_calls += 1
            print(f"\r  検索中... API呼び出し {api_calls}/{MAX_API_CALLS} 回目 (今回確保: {len(new_feed)}件)", end="")

            params = {
                'q': '*',        # 検索クエリ
                'lang': 'ja',    # 日本語
                'limit': 100,    # 1回あたりの取得数
                'sort': 'latest' # 最新順
            }
            if cursor:
                params['cursor'] = cursor

            response = client.app.bsky.feed.search_posts(params=params)
            
            if not response.posts:
                print("\n  これ以上取得できる投稿がありません。")
                break
                
            # 取得した投稿をフィルタリング
            for post in response.posts:
                if len(new_feed) >= MAX_NEW_POSTS_THIS_RUN:
                    break

                # 1. 重複チェック
                if post.uri in existing_uris:
                    continue
                
                if not hasattr(post.record, 'text') or not post.record.text:
                    continue
                    
                text = post.record.text.strip()
                if not text or text in existing_texts:
                    continue

                # 2. 文字数チェック（ここが重要！）
                length = len(text)
                bin_idx = get_bin_index(length)
                
                # 範囲外ならスキップ
                if bin_idx == -1:
                    continue

                # 目標件数に達しているビンの投稿はスキップ（重要）
                # ※ただし、今回追加分も含めて判定する
                current_count_in_bin = current_bin_counts[bin_idx]
                # new_feed内の同じビンの数をカウント
                new_count_in_bin = sum(1 for p in new_feed if get_bin_index(len(p.record.text.strip())) == bin_idx)
                
                if (current_count_in_bin + new_count_in_bin) >= TARGET_COUNT_PER_BIN:
                    # この文字数帯はもう十分なのでスキップ
                    continue
                
                # 採用！
                new_feed.append(post)
                existing_uris.add(post.uri)
                existing_texts.add(text)

            cursor = response.cursor
            
            if not cursor:
                print("\n  カーソルが返されませんでした。検索を終了します。")
                break
            
            # API負荷軽減
            time.sleep(1.0)

    except Exception as e:
        print(f"\n\n⚠️ 投稿の検索中にエラーが発生しました: {e}")
        return

    print("\n") # 改行

    if not new_feed:
        print("条件に合う新しい投稿が見つかりませんでした。（長い文章は希少です。時間をおいて再実行してください）")
        return

    print(f"条件に合う {len(new_feed)} 件の投稿を確保しました。詳細情報の取得と分析を行います。")

    posts_data_for_llm = []
    original_posts_info = []
    author_profile_cache = {}

    # 詳細情報の取得
    for i, post in enumerate(new_feed):
        print(f"  メタデータ取得中: {i+1}/{len(new_feed)}...", end="\r")
        text = post.record.text.strip()
        author_did = post.author.did
            
        if author_did not in author_profile_cache:
            try:
                full_profile = client.get_profile(actor=author_did)
                author_profile_cache[author_did] = full_profile
                time.sleep(0.1) 
            except Exception:
                author_profile_cache[author_did] = None
        
        full_author_profile = author_profile_cache[author_did]
        followers_count = full_author_profile.followers_count if full_author_profile else 0
        follows_count = full_author_profile.follows_count if full_author_profile else 0
        
        posts_data_for_llm.append(text)
        
        original_posts_info.append({
            "post_text": text,
            "text_length": len(text),
            "author_handle": post.author.handle,
            "followers_count": followers_count,
            "follows_count": follows_count,
            "post_uri": post.uri
        })
    
    print("\n--- LLMで分類を開始します ---")
    try:
        llm_results = llm_analyzer.analyze_posts_batch(posts_data_for_llm)
    except Exception as e:
        print(f"⚠️ LLMによる分析中にエラーが発生しました: {e}")
        return

    # 分析失敗チェック
    failed_count = 0
    for res in llm_results:
        if res.get('content_category') == '分析失敗':
            failed_count += 1
    
    if failed_count > 0:
        print(f"⚠️ {failed_count}件の分析に失敗したため、保存を中止します。")
        return

    # データの結合
    final_data = []
    for i, post_info in enumerate(original_posts_info):
        llm_result = llm_results[i]
        post_info.update({
            "content_category": llm_result.get('content_category'),
            "expression_category": llm_result.get('expression_category'),
            "style_stance_category": llm_result.get('style_stance_category')
        })
        final_data.append(post_info)

    # --- ファイルへの保存 ---
    
    # 1. テキストファイル
    text_wrapper = textwrap.TextWrapper(width=95, subsequent_indent='    ')
    mode_txt = 'a' if os.path.exists(TXT_FILE) else 'w'
    
    try:
        with open(TXT_FILE, mode_txt, encoding='utf-8') as f:
            if mode_txt == 'w':
                f.write("="*100 + "\n【Bluesky 公開日本語投稿 分析結果】\n" + "="*100 + "\n")
            
            for i, data in enumerate(final_data):
                current_num = next_post_index + i
                f.write(f"\n【投稿 {current_num}】\n")
                f.write(f"  著者: @{data['author_handle']}\n")
                f.write(f"  文字: {data['text_length']} 文字\n")
                f.write(f"  URI : {data['post_uri']}\n")
                f.write("  ---\n")
                f.write(f"  本文: {text_wrapper.fill(data['post_text'])}\n")
                f.write("  ---\n")
                f.write(f"  分析: [コンテンツ] {data['content_category']}\n")
                f.write(f"        [表現(感情)] {data['expression_category']}\n")
                f.write(f"        [スタイル] {data['style_stance_category']}\n")
                f.write("-" * 98 + "\n")
    except Exception as e:
        print(f"⚠️ テキストファイル保存エラー: {e}")
        return

    # 2. CSVファイル
    headers = [
        "post_uri", "post_text", "llm_content_category", "is_content_correct (0 or 1)",
        "llm_expression_category", "is_expression_correct (0 or 1)",
        "llm_style_stance_category", "is_style_correct (0 or 1)"
    ]
    mode_csv = 'a' if os.path.exists(CSV_FILE) else 'w'

    try:
        with open(CSV_FILE, mode_csv, encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            if mode_csv == 'w':
                writer.writerow(headers)
            
            for data in final_data:
                writer.writerow([
                    data['post_uri'],
                    data['post_text'],
                    data['content_category'], "", 
                    data['expression_category'], "", 
                    data['style_stance_category'], "" 
                ])
        print(f"✅ {len(final_data)} 件のデータを追加保存しました！")
        
        # 最終的な内訳を表示
        print("\n【今回の追加内訳】")
        added_counts = [0] * len(BINS)
        for data in final_data:
            idx = get_bin_index(data['text_length'])
            if idx != -1:
                added_counts[idx] += 1
        
        for i, label in enumerate(BIN_LABELS):
            if added_counts[i] > 0:
                print(f"  {label}: +{added_counts[i]} 件")

    except Exception as e:
        print(f"⚠️ CSV保存エラー: {e}")

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    fetch_and_export_timeline()