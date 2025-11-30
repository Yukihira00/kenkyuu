import os
from atproto import Client, models

class FeedViewPostWrapper:
    def __init__(self, post, reason=None):
        self.post = post
        self.reply = None
        self.reason = reason  # リポスト情報など

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

def get_timeline_data(handle: str, app_password: str, limit: int = 100, cursor: str = None, feed_type: str = 'search'):
    """
    feed_type: 'search' (最新の投稿/全体) または 'timeline' (フォロー中)
    """
    client = Client()
    try:
        client.login(handle, app_password)
        
        # --- A. フォロー中のタイムラインを取得 ---
        if feed_type == 'timeline':
            params = {'limit': limit}
            if cursor:
                params['cursor'] = cursor
            
            # フォロー中のTLを取得
            response = client.get_timeline(**params)
            
            # get_timeline の戻り値は FeedViewPost のリスト (item.post, item.reason 等が含まれる)
            wrapped_feed = []
            for item in response.feed:
                # item.post が PostView オブジェクト
                wrapper = FeedViewPostWrapper(item.post, item.reason)
                wrapped_feed.append(wrapper)
                
            return wrapped_feed, response.cursor

        # --- B. 最新の投稿（検索）を取得 (デフォルト) ---
        else:
            params = {
                'q': '*',         # 全文検索（実質的なGlobal Timeline）
                'lang': 'ja',     # 日本語のみ
                'limit': limit,
                'sort': 'latest'
            }
            if cursor:
                params['cursor'] = cursor
            
            response = client.app.bsky.feed.search_posts(params=params)
            
            if not response.posts:
                return [], None

            # search_posts の戻り値は PostView のリスト
            wrapped_feed = [FeedViewPostWrapper(post) for post in response.posts]
            
            return wrapped_feed, response.cursor

    except Exception as e:
        print(f"タイムライン取得エラー ({feed_type}): {e}")
        return None, None