# export_timeline_for_analysis.py
import os
import llm_analyzer
import timeline_checker 
from dotenv import load_dotenv
import sys
from atproto import Client
import time
import textwrap

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')

BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

def fetch_and_export_timeline():
    """
    あなたのBlueskyタイムラインから投稿を取得し、重複（リポスト・同一内容）を除外し、
    詳細情報と共にLLMで分類し、結果をテキストファイルに出力する。
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
    
    print(f"Bluesky ({BSKY_HANDLE}) のタイムラインを取得しています... (最大100件)")
    
    try:
        raw_feed = timeline_checker.get_timeline_data(BSKY_HANDLE, BSKY_APP_PASSWORD, limit=100)
    except Exception as e:
        print(f"タイムラインの取得中にエラーが発生しました: {e}")
        return

    if not raw_feed:
        print("タイムラインの取得に失敗したか、表示できる投稿がありません。")
        return

    # ▼▼▼ 【修正箇所】 同一テキスト内容の重複排除ロジックを追加 ▼▼▼
    
    feed = []
    seen_uris = set()
    seen_texts = set() # ◀◀◀ 【追加】 処理済みのテキスト内容を記憶
    
    repost_count = 0
    duplicate_text_count = 0 # ◀◀◀ 【追加】
    
    for item in raw_feed: # item は FeedViewPost
        
        # 1. 純粋なリポスト(reasonが存在)する場合は除外する
        if item.reason:
            repost_count += 1
            continue
            
        # 2. 投稿URIで重複チェック (APIが同じものを返す場合)
        if item.post.uri in seen_uris:
            continue
            
        # 3. テキスト内容を取得 (リポストでない投稿のみ)
        if hasattr(item.post.record, 'text') and item.post.record.text:
            text = item.post.record.text.strip()
            
            if not text: # 空の投稿はスキップ
                continue
                
            # 4. ◀◀◀ 【追加】 テキスト内容が重複していないかチェック
            if text in seen_texts:
                duplicate_text_count += 1
                continue
            # ◀◀◀ 【追加ここまで】
            
            # すべてのチェックを通過
            feed.append(item)
            seen_uris.add(item.post.uri)
            seen_texts.add(text) # ◀◀◀ 【追加】 処理済みテキストとして記憶
        
    print(f"タイムラインから {len(raw_feed)}件取得。")
    print(f"  純粋なリポスト {repost_count}件を除外しました。")
    print(f"  内容が重複する投稿 {duplicate_text_count}件を除外しました。") # ◀◀◀ 【追加】
    print(f"  重複を除外した {len(feed)}件（ユニークな内容の投稿）を処理します。")
    # ▲▲▲ 【修正ここまで】 ▲▲▲

    posts_data_for_llm = []
    original_posts_info = []
    author_profile_cache = {}

    print("投稿情報を処理中... (著者プロフィールを取得するため、時間がかかります)")
    
    for i, item in enumerate(feed):
        
        # item.post.record からテキストを取得 (チェック済み)
        text = item.post.record.text.strip()
        author_did = item.post.author.did
            
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
        
        posts_data_for_llm.append(text)
        
        original_posts_info.append({
            "post_text": text,
            "text_length": len(text),
            "author_handle": item.post.author.handle,
            "followers_count": followers_count,
            "follows_count": follows_count,
            "post_uri": item.post.uri
        })

    if not posts_data_for_llm:
        print("分析対象のテキスト投稿がありませんでした。")
        return

    print(f"--- {len(posts_data_for_llm)}件の投稿をLLMで分類します ---")
    print("（APIへの問い合わせとベクトル化のため、数十秒かかる場合があります）")

    try:
        llm_results = llm_analyzer.analyze_posts_batch(posts_data_for_llm)
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

    print("--- 分析結果をテキストファイルに出力します ---")
    
    output_lines = []
    TEXT_WIDTH = 100 
    text_wrapper = textwrap.TextWrapper(width=TEXT_WIDTH - 5,
                                      subsequent_indent='    ')

    output_lines.append("="*TEXT_WIDTH)
    output_lines.append("【Bluesky タイムライン分析結果 (リポスト・同一内容除外)】")
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

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            print("Warning: Failed to reconfigure stdout/stderr to UTF-8.")
            
    fetch_and_export_timeline()