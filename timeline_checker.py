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


def get_timeline_data(handle: str, app_password: str, limit: int = 30):
    """
    指定されたアカウント情報でログインし、タイムラインのデータを取得して返す。
    成功した場合は投稿のリスト、失敗した場合はNoneを返す。
    """
    client = Client()
    try:
        client.login(handle, app_password)
        response = client.get_timeline(limit=limit)
        return response.feed
    except Exception as e:
        print(f"タイムライン取得エラー: {e}")
        return None