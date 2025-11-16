# timeline_checker.py
import os
from atproto import Client, models

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


def get_timeline_data(handle: str, app_password: str, limit: int = 50):
    """
    指定されたアカウント情報でログインし、フォローしている人のタイムラインを取得して返す。
    指定されたlimit件数に達するまでページネーションを行う。
    """
    client = Client()
    try:
        client.login(handle, app_password)
        
        # ▼▼▼ 100件以上取得するためにページネーションを実装 ▼▼▼
        all_feed_items = []
        cursor = None
        REQUEST_LIMIT = 100  # 1回あたりの最大取得件数 (Blueskyのget_timelineは最大100)
        
        print(f"タイムラインを取得しています... (最大 {limit} 件)")
        
        while len(all_feed_items) < limit:
            remaining = limit - len(all_feed_items)
            current_limit = min(remaining, REQUEST_LIMIT)
            if current_limit <= 0:
                break
                
            print(f"  ... {len(all_feed_items)}件取得済み。追加で{current_limit}件を取得します ...")
            
            # get_timeline に limit と cursor をキーワード引数として渡す
            response = client.get_timeline(limit=current_limit, cursor=cursor)
            
            if not response.feed:
                print("  これ以上取得できる投稿がありません。")
                break
                
            all_feed_items.extend(response.feed)
            cursor = response.cursor
            
            if not cursor:
                print("  カーソルが返されませんでした。取得を終了します。")
                break
        
        return all_feed_items
        
    except Exception as e:
        print(f"タイムライン取得エラー: {e}")
        return None