import os
from atproto import Client, models

class FeedViewPostWrapper:
    def __init__(self, post):
        self.post = post
        self.reply = None
        self.reason = None

def verify_login_and_get_profile(handle: str, app_password: str):
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

# ▼▼▼ cursor引数を追加し、戻り値を (posts, cursor) に変更 ▼▼▼
def get_timeline_data(handle: str, app_password: str, limit: int = 100, cursor: str = None):
    client = Client()
    try:
        client.login(handle, app_password)
        
        params = {
            'q': '*',
            'lang': 'ja',
            'limit': limit,
            'sort': 'latest'
        }
        if cursor:
            params['cursor'] = cursor
        
        response = client.app.bsky.feed.search_posts(params=params)
        
        if not response.posts:
            return [], None

        wrapped_feed = [FeedViewPostWrapper(post) for post in response.posts]
        
        # 投稿と次のページ用カーソルを返す
        return wrapped_feed, response.cursor

    except Exception as e:
        print(f"タイムライン（検索）取得エラー: {e}")
        return None, None