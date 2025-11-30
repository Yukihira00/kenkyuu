import os
from atproto import Client, models

# メイン側(main.py)で item.post.uri のようにアクセスしているため、
# 検索結果(PostView)をラップして、構造を合わせるためのクラス
class FeedViewPostWrapper:
    def __init__(self, post):
        self.post = post
        self.reply = None
        self.reason = None

def verify_login_and_get_profile(handle: str, app_password: str):
    """
    ログインを試み、成功したらプロフィール情報を辞書として返す。
    失敗した場合はNoneを返す。
    """
    client = Client()
    try:
        profile = client.login(handle, app_password)
        return {
            "did": profile.did,
            "handle": profile.handle,
            "display_name": profile.display_name
        }
    except Exception as e:
        print(f"ログイン失敗: {e}")
        return None


def get_timeline_data(handle: str, app_password: str, limit: int = 100):
    """
    指定されたアカウント情報でログインし、
    日本語の投稿を検索して広範囲に取得する（精度調整時と同様のロジック）。
    戻り値は main.py との互換性のため、FeedViewPostWrapper のリストとする。
    """
    client = Client()
    try:
        client.login(handle, app_password)
        
        # ▼▼▼ 変更: フォローのTLではなく、検索APIで日本語投稿を広く取得する ▼▼▼
        # 精度調整スクリプトと同じく、日本語の最新投稿を対象にします
        params = {
            'q': '*',        # 全てのキーワード
            'lang': 'ja',    # 日本語のみ
            'limit': limit,  # 指定件数（通常API上限は100）
            'sort': 'latest' # 最新順
        }
        
        response = client.app.bsky.feed.search_posts(params=params)
        
        if not response.posts:
            return []

        # main.py が期待する形式 (item.post) にラップして返す
        wrapped_feed = [FeedViewPostWrapper(post) for post in response.posts]
        
        return wrapped_feed

    except Exception as e:
        print(f"タイムライン（検索）取得エラー: {e}")
        return None