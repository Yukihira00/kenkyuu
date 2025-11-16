# export_timeline_for_analysis.py
import os
import llm_analyzer
from dotenv import load_dotenv
import sys
from atproto import Client
import time  # ◀ time モジュールが使われることを確認 (既にインポートされています)
import textwrap
import csv

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')

BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

def fetch_and_export_timeline():
    """
    Blueskyから日本語の公開投稿を取得し、重複（同一内容）を除外し、
    詳細情報と共にLLMで分類し、結果をテキストファイルと採点用CSVに出力する。
    """
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("エラー: .envファイルに BSKY_HANDLE と BSKY_APP_PASSWORD を設定してください。")
        return

    # Blueskyクライアントを初期化・ログイン
    client = Client()
    try:
        client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
        print(f"Bluesky ({BSKY_HANDLE}) にログインしました。")
    except Exception as e:
        print(f"Blueskyへのログインに失敗しました: {e}")
        return
    
    # ▼▼▼ 【変更箇所】 1000件取得するようにページネーション処理を追加 ▼▼▼
    print(f"Blueskyから日本語の投稿を検索しています... (最大1000件)")
    
    all_raw_posts = []
    cursor = None
    TARGET_COUNT = 1000
    REQUEST_LIMIT = 100  # APIの1回あたりの最大取得件数

    try:
        while len(all_raw_posts) < TARGET_COUNT:
            print(f"  ... {len(all_raw_posts)}件取得済み。追加で{REQUEST_LIMIT}件を検索します ...")

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
                
            all_raw_posts.extend(response.posts)
            cursor = response.cursor
            
            if not cursor:
                print("  カーソルが返されませんでした。検索を終了します。")
                break
            
            time.sleep(0.5)  # API負荷軽減のための待機

        raw_posts = all_raw_posts[:TARGET_COUNT]  # 厳密にTARGET_COUNT件にする
        
    except Exception as e:
        print(f"投稿の検索中にエラーが発生しました: {e}")
        return
    # ▲▲▲ 【変更箇所ここまで】 ▲▲▲

    if not raw_posts:
        print("検索結果の取得に失敗したか、表示できる投稿がありません。")
        return

    # ▼▼▼ 重複排除ロジック (変更なし) ▼▼▼
    
    feed = [] # ここには PostView が入る
    seen_uris = set()
    seen_texts = set()
    
    duplicate_text_count = 0
    
    for post in raw_posts: # post は PostView
        
        if post.uri in seen_uris:
            continue
            
        if hasattr(post.record, 'text') and post.record.text:
            text = post.record.text.strip()
            
            if not text:
                continue
                
            if text in seen_texts:
                duplicate_text_count += 1
                continue
            
            feed.append(post)
            seen_uris.add(post.uri)
            seen_texts.add(text)
        
    print(f"検索で {len(raw_posts)}件取得。")
    print(f"  内容が重複する投稿 {duplicate_text_count}件を除外しました。")
    print(f"  重複を除外した {len(feed)}件（ユニークな内容の投稿）を処理します。")

    posts_data_for_llM = []
    original_posts_info = []
    author_profile_cache = {}

    print("投稿情報を処理中... (著者プロフィールを取得するため、時間がかかります)")
    
    for i, post in enumerate(feed):
        
        text = post.record.text.strip()
        author_did = post.author.did
            
        if author_did not in author_profile_cache:
            try:
                full_profile = client.get_profile(actor=author_did)
                author_profile_cache[author_did] = full_profile
                print(f"  {i+1}/{len(feed)}: {full_profile.handle} のプロフィール取得完了")
                time.sleep(0.1) 
            except Exception as e:
                print(f"  警告: {author_did} のプロフィール取得に失敗: {e}")
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

    if not posts_data_for_llM:
        print("分析対象のテキスト投稿がありませんでした。")
        return

    print(f"--- {len(posts_data_for_llM)}件の投稿をLLMで分類します ---")
    print("（APIへの問い合わせとベクトル化のため、数十秒かかる場合があります）")

    try:
        llm_results = llm_analyzer.analyze_posts_batch(posts_data_for_llM)
    except Exception as e:
        print(f"LLMによる分析中にエラーが発生しました: {e}")
        return

    final_data = []
    for i, post_info in enumerate(original_posts_info):
        llm_result = llm_results[i]
        post_info.update({
            "content_category": llm_result.get('content_category'),
            "expression_category": llm_result.get('expression_category'),
            "style_stance_category": llm_result.get('style_stance_category')
        })
        final_data.append(post_info)

    # --- 1. テキストファイルへの出力 (変更なし) ---
    print("--- 分析結果をテキストファイルに出力します ---")
    
    output_lines = []
    TEXT_WIDTH = 100 
    text_wrapper = textwrap.TextWrapper(width=TEXT_WIDTH - 5,
                                      subsequent_indent='    ')

    output_lines.append("="*TEXT_WIDTH)
    output_lines.append("【Bluesky 公開日本語投稿 分析結果 (重複除外)】")
    output_lines.append("="*TEXT_WIDTH)

    for i, data in enumerate(final_data):
        output_lines.append(f"\n【投稿 {i+1} / {len(final_data)}】")
        output_lines.append(f"  著者: @{data['author_handle']}")
        output_lines.append(f"  統計: {data['followers_count']} フォロワー / {data['follows_count']} フォロー")
        output_lines.append(f"  文字: {data['text_length']} 文字")
        output_lines.append(f"  URI : {data['post_uri']}")
        output_lines.append("  ---")
        
        wrapped_text = text_wrapper.fill(data['post_text'])
        output_lines.append(f"  本文: {wrapped_text}")
        output_lines.append("  ---")
        
        output_lines.append(f"  分析: [コンテンツ] {data['content_category']}")
        output_lines.append(f"        [表現(感情)] {data['expression_category']}")
        output_lines.append(f"        [スタイル] {data['style_stance_category']}")
        output_lines.append("-"*(TEXT_WIDTH - 2))
    
    output_filename_txt = "timeline_analysis_export.txt"
    try:
        full_output_text = "\n".join(output_lines)
        
        with open(output_filename_txt, 'w', encoding='utf-8') as f:
            f.write(full_output_text)
            
        print(f"\n✅ データを '{output_filename_txt}' に正常に出力しました。")
    
    except Exception as e:
        print(f"\nテキストファイルへの書き込み中にエラーが発生しました: {e}")


    # --- 2. ◀◀◀【ここから修正】0/1採点用のCSVファイル出力 ---
    print("--- 統計チェック用のCSVファイルを出力します ---")
    output_filename_csv = "analysis_for_checking_01.csv" # ◀ ファイル名を変更
    
    # CSVのヘッダー（列名）を修正
    headers = [
        "post_uri", 
        "post_text", 
        "llm_content_category", 
        "is_content_correct (0 or 1)",      # ◀ 人が 0 か 1 を入力する列
        "llm_expression_category", 
        "is_expression_correct (0 or 1)", # ◀ 人が 0 か 1 を入力する列
        "llm_style_stance_category",
        "is_style_correct (0 or 1)"  # ◀ 人が 0 か 1 を入力する列
    ]

    try:
        with open(output_filename_csv, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            
            for data in final_data:
                writer.writerow([
                    data['post_uri'],
                    data['post_text'],
                    data['content_category'],
                    "", # is_content_correct (空欄)
                    data['expression_category'],
                    "", # is_expression_correct (空欄)
                    data['style_stance_category'],
                    ""  # is_style_correct (空欄)
                ])
        
        print(f"✅ 統計チェック用データを '{output_filename_csv}' に正常に出力しました。")
    
    except Exception as e:
        print(f"\nCSVファイルへの書き込み中にエラーが発生しました: {e}")
    # --- ◀◀◀【修正ここまで】 ---


if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            print("Warning: Failed to reconfigure stdout/stderr to UTF-8.")
            
    fetch_and_export_timeline()