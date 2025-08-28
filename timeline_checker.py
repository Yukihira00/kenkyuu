import os
from atproto import Client

def main():
    # 環境変数からBlueskyのハンドル名とパスワードを取得
    bluesky_handle = os.environ.get('BLUESKY_HANDLE')
    bluesky_password = os.environ.get('BLUESKY_PASSWORD')

    # ハンドル名かパスワードが設定されていない場合はエラーを表示して終了
    if not bluesky_handle or not bluesky_password:
        print("エラー: 環境変数 BLUESKY_HANDLE と BLUESKY_PASSWORD を設定してください。")
        return

    print(f"{bluesky_handle}としてログインを試みます...")

    # Blueskyクライアントの初期化
    client = Client()
    
    try:
        # ログイン処理
        profile = client.login(bluesky_handle, bluesky_password)
        print("✅ ログイン成功！")
        print(f"ようこそ, {profile.display_name} (@{profile.handle}) さん")

        # タイムラインを取得
        print("\nタイムラインを取得中...")
        # limit=20 で最大20件の投稿を取得
        response = client.get_timeline(limit=20) 
        
        if not response.feed:
            print("タイムラインに投稿がありません。")
            return

        print("✅ タイムライン取得成功！ 最新の投稿をいくつか表示します。")
        print("-" * 30)

        # 取得した投稿を一つずつ表示
        for feed_view in response.feed:
            post = feed_view.post
            author = post.author
            # 投稿内容が長すぎる場合は100文字に省略
            post_text = (post.record.text[:100] + '...') if len(post.record.text) > 100 else post.record.text
            
            print(f"👤 {author.display_name} (@{author.handle})")
            print(f"   {post_text.replace('\n', '\n   ')}") # 投稿内の改行をインデント
            print("-" * 30)

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")

if __name__ == "__main__":
    main()