# check_bluesky_classification.py
import os
import llm_analyzer
import timeline_checker
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv(encoding='utf-8')

# .envファイルからBlueskyのログイン情報を取得
# 注意: .envファイルにこれらの変数を追加する必要があります
BSKY_HANDLE = os.getenv('BSKY_HANDLE')
BSKY_APP_PASSWORD = os.getenv('BSKY_APP_PASSWORD')

def fetch_and_classify_timeline():
    """
    Blueskyのタイムラインから投稿を取得し、LLMで分類してターミナルに出力する。
    .envファイルに BSKY_HANDLE と BSKY_APP_PASSWORD が必要。
    """
    if not BSKY_HANDLE or not BSKY_APP_PASSWORD:
        print("エラー: .envファイルに BSKY_HANDLE と BSKY_APP_PASSWORD を設定してください。")
        print("（.envファイルに以下の2行を追記してください）")
        print("BSKY_HANDLE=your-handle.bsky.social")
        print("BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx")
        return

    print(f"Bluesky ({BSKY_HANDLE}) からタイムラインを取得しています... (最大100件)")
    
    # timeline_checker を使ってタイムラインデータを取得 (limit=100 を指定)
    feed = timeline_checker.get_timeline_data(BSKY_HANDLE, BSKY_APP_PASSWORD, limit=100)

    if not feed:
        print("タイムラインの取得に失敗したか、表示できる投稿がありません。")
        return

    # テキストデータのみを抽出
    texts_to_analyze = []
    original_posts = []
    for item in feed:
        # リポストやテキストのない投稿を除外
        if hasattr(item.post.record, 'text') and item.post.record.text:
            text = item.post.record.text.strip()
            if text: # 空の投稿を除外
                texts_to_analyze.append(text)
                original_posts.append(text) # 元のテキストも保持

    if not texts_to_analyze:
        print("分析対象のテキスト投稿がありませんでした。")
        return

    print(f"--- {len(texts_to_analyze)}件のBluesky投稿を分類します ---")
    print("（APIへの問い合わせとベクトル化のため、数十秒かかる場合があります）")

    # llm_analyzerのバッチ分析関数を呼び出す
    results = llm_analyzer.analyze_posts_batch(texts_to_analyze)

    print("\n--- 分類結果 ---")

    # 読みやすい形式で出力
    for i, (text, result) in enumerate(zip(original_posts, results)):
        
        # ▼▼▼【変更箇所】▼▼▼
        # 文字数で省略する処理を削除し、全文を表示するように変更。
        # 投稿ごと区切り線を入れて見やすくします。
        print(f"\n【投稿 {i+1}】")
        print(text) # 元のテキスト(全文)をそのまま出力
        print(f"  - コンテンツ  : {result.get('content_category')}")
        print(f"  - 表現（感情）: {result.get('expression_category')}")
        print(f"  - スタイル    : {result.get('style_stance_category')}")
        # ▲▲▲【変更箇所ここまで】▲▲▲
    
    print("\n--- チェック完了 ---")

if __name__ == "__main__":
    fetch_and_classify_timeline()