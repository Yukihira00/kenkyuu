# export_timeline_for_analysis.py
import os
import llm_analyzer
from dotenv import load_dotenv
import sys
from atproto import Client
import time
import textwrap
import csv

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')

BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

# 出力ファイル名
CSV_FILE = "analysis_for_checking_01.csv"
TXT_FILE = "timeline_analysis_export.txt"

def fetch_and_export_timeline():
    """
    Blueskyから日本語の公開投稿を取得し、重複（同一内容）を除外し、
    詳細情報と共にLLMで分類し、結果をテキストファイルと採点用CSVに追加（追記）する。
    ※エラーや分析失敗が一つでもあれば保存しない。
    """
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("エラー: .envファイルに BSKY_HANDLE と BSKY_APP_PASSWORD を設定してください。")
        return

    # 1. 既存データの読み込み（重複チェック用）
    existing_uris = set()
    existing_texts = set()
    next_post_index = 1

    if os.path.exists(CSV_FILE):
        print(f"既存のファイル '{CSV_FILE}' を読み込んでいます...")
        try:
            with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_uris.add(row['post_uri'])
                    if 'post_text' in row:
                        existing_texts.add(row['post_text'])
            next_post_index = len(existing_uris) + 1
            print(f"  -> 既存データ: {len(existing_uris)}件 (No.{next_post_index} から追記します)")
        except Exception as e:
            print(f"  -> 警告: 既存ファイルの読み込みに失敗しました ({e})。新規作成として扱います。")

    # Blueskyクライアントを初期化・ログイン
    client = Client()
    try:
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
        print(f"Bluesky ({BSKY_HANDLE}) にログインしました。")
    except Exception as e:
        print(f"Blueskyへのログインに失敗しました: {e}")
        return
    
    TARGET_ADD_COUNT = 100
    print(f"Blueskyから新しい日本語の投稿を検索しています... (目標追加数: {TARGET_ADD_COUNT}件)")
    
    new_feed = [] # ここには PostView が入る
    cursor = None
    REQUEST_LIMIT = 100  # APIの1回あたりの最大取得件数
    
    # 検索ループ
    MAX_API_CALLS = 50 
    api_calls = 0
    
    try:
        while len(new_feed) < TARGET_ADD_COUNT and api_calls < MAX_API_CALLS:
            print(f"  ... API呼び出し {api_calls+1}/{MAX_API_CALLS}回目 (現在確保数: {len(new_feed)}/{TARGET_ADD_COUNT}) ...")

            params = {
                'q': '*',        # 検索クエリ (ワイルドカード)
                'lang': 'ja',   # 言語を日本語に指定
                'limit': REQUEST_LIMIT,
                'sort': 'latest' # 最新の投稿を取得
            }
            if cursor:
                params['cursor'] = cursor

            response = client.app.bsky.feed.search_posts(params=params)
            
            if not response.posts:
                print("  これ以上取得できる投稿がありません。")
                break
                
            # 重複チェックとフィルタリング
            for post in response.posts:
                if len(new_feed) >= TARGET_ADD_COUNT:
                    break

                # URIで重複チェック
                if post.uri in existing_uris:
                    continue
                
                # テキスト有無チェック
                if not hasattr(post.record, 'text') or not post.record.text:
                    continue
                    
                text = post.record.text.strip()
                if not text:
                    continue
                    
                # テキスト内容で重複チェック
                if text in existing_texts:
                    continue
                
                # 採用
                new_feed.append(post)
                existing_uris.add(post.uri)
                existing_texts.add(text)

            cursor = response.cursor
            api_calls += 1
            
            if not cursor:
                print("  カーソルが返されませんでした。検索を終了します。")
                break
            
            time.sleep(1.0)  # API負荷軽減

    except Exception as e:
        print(f"⚠️ 投稿の検索中にエラーが発生しました: {e}")
        print("処理を中断します。ファイルへの書き込みは行われません。")
        return

    if not new_feed:
        print("新しい投稿が見つかりませんでした。")
        return

    print(f"新規に {len(new_feed)} 件の投稿を確保しました。詳細情報の取得と分析を行います。")

    posts_data_for_llM = []
    original_posts_info = []
    author_profile_cache = {}

    try:
        for i, post in enumerate(new_feed):
            print(f"  処理中: {i+1}/{len(new_feed)}...")
            text = post.record.text.strip()
            author_did = post.author.did
                
            if author_did not in author_profile_cache:
                try:
                    full_profile = client.get_profile(actor=author_did)
                    author_profile_cache[author_did] = full_profile
                    time.sleep(0.1) 
                except Exception as e:
                    print(f"    警告: {author_did} のプロフィール取得に失敗: {e}")
                    author_profile_cache[author_did] = None
            
            full_author_profile = author_profile_cache[author_did]
            
            followers_count = full_author_profile.followers_count if full_author_profile else None
            follows_count = full_author_profile.follows_count if full_author_profile else None
            
            posts_data_for_llM.append(text)
            
            original_posts_info.append({
                "post_text": text,
                "text_length": len(text),
                "author_handle": post.author.handle,
                "followers_count": followers_count,
                "follows_count": follows_count,
                "post_uri": post.uri
            })
    except Exception as e:
        print(f"⚠️ 投稿詳細情報の取得中にエラーが発生しました: {e}")
        print("処理を中断します。ファイルへの書き込みは行われません。")
        return

    if not posts_data_for_llM:
        print("分析対象のテキスト投稿がありませんでした。")
        return

    print(f"--- {len(posts_data_for_llM)}件の投稿をLLMで分類します ---")
    try:
        llm_results = llm_analyzer.analyze_posts_batch(posts_data_for_llM)
    except Exception as e:
        print(f"⚠️ LLMによる分析中にエラーが発生しました: {e}")
        print("処理を中断します。ファイルへの書き込みは行われません。")
        return

    # ▼▼▼ 【変更箇所】 分析失敗チェック ▼▼▼
    failed_count = 0
    for res in llm_results:
        # llm_analyzer はエラー時に "分析失敗" という文字列を入れる仕様になっている前提
        if (res.get('content_category') == '分析失敗' or 
            res.get('expression_category') == '分析失敗' or 
            res.get('style_stance_category') == '分析失敗'):
            failed_count += 1
    
    if failed_count > 0:
        print(f"\n⚠️ {failed_count}件の投稿で分析に失敗しました。")
        print("データの整合性を保つため、今回の取得分は破棄し、ファイルへの保存を中止します。")
        print("（API制限や一時的な通信エラーの可能性があります。しばらく待ってから再実行してください）")
        return
    # ▲▲▲ 【変更箇所ここまで】 ▲▲▲

    # ここまで来たら全件成功しているのでデータを結合
    final_data = []
    for i, post_info in enumerate(original_posts_info):
        llm_result = llm_results[i]
        post_info.update({
            "content_category": llm_result.get('content_category'),
            "expression_category": llm_result.get('expression_category'),
            "style_stance_category": llm_result.get('style_stance_category')
        })
        final_data.append(post_info)

    # --- 1. テキストファイルへの追記 ---
    print(f"--- 分析結果を '{TXT_FILE}' に追記します ---")
    
    text_wrapper = textwrap.TextWrapper(width=95, subsequent_indent='    ')
    
    mode_txt = 'a' if os.path.exists(TXT_FILE) else 'w'
    
    try:
        with open(TXT_FILE, mode_txt, encoding='utf-8') as f:
            if mode_txt == 'w':
                f.write("="*100 + "\n")
                f.write("【Bluesky 公開日本語投稿 分析結果】\n")
                f.write("="*100 + "\n")
            
            for i, data in enumerate(final_data):
                current_num = next_post_index + i
                
                f.write(f"\n【投稿 {current_num}】\n")
                f.write(f"  著者: @{data['author_handle']}\n")
                f.write(f"  統計: {data['followers_count']} フォロワー / {data['follows_count']} フォロー\n")
                f.write(f"  文字: {data['text_length']} 文字\n")
                f.write(f"  URI : {data['post_uri']}\n")
                f.write("  ---\n")
                
                wrapped_text = text_wrapper.fill(data['post_text'])
                f.write(f"  本文: {wrapped_text}\n")
                f.write("  ---\n")
                
                f.write(f"  分析: [コンテンツ] {data['content_category']}\n")
                f.write(f"        [表現(感情)] {data['expression_category']}\n")
                f.write(f"        [スタイル] {data['style_stance_category']}\n")
                f.write("-" * 98 + "\n")
                
        print("✅ テキストファイルへの出力完了")

    except Exception as e:
        print(f"\n⚠️ テキストファイルへの書き込み中にエラーが発生しました: {e}")
        print("注意: CSVファイルへの書き込みは行われません。")
        return

    # --- 2. CSVファイルへの追記 ---
    print(f"--- 統計チェック用データを '{CSV_FILE}' に追記します ---")
    
    headers = [
        "post_uri", 
        "post_text", 
        "llm_content_category", 
        "is_content_correct (0 or 1)",
        "llm_expression_category", 
        "is_expression_correct (0 or 1)",
        "llm_style_stance_category",
        "is_style_correct (0 or 1)"
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
                    data['content_category'],
                    "", 
                    data['expression_category'],
                    "", 
                    data['style_stance_category'],
                    "" 
                ])
        
        print("✅ CSVファイルへの出力完了")
    
    except Exception as e:
        print(f"\n⚠️ CSVファイルへの書き込み中にエラーが発生しました: {e}")


if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            print("Warning: Failed to reconfigure stdout/stderr to UTF-8.")
            
    fetch_and_export_timeline()