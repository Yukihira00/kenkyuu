# delete_cache.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def delete_cache_and_related_feedback():
    """unpleasant_feedbackテーブルとpost_analysis_cacheテーブルの全データを削除する"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        cur = conn.cursor()

        # ▼▼▼【追加】unpleasant_feedbackテーブルのデータを先に削除 ▼▼▼
        print("1. unpleasant_feedback テーブルのデータを削除しています...")
        cur.execute("DELETE FROM unpleasant_feedback;")
        print("✅ unpleasant_feedback テーブルのデータを削除しました。")

        # ▼▼▼【変更】次にpost_analysis_cacheテーブルのデータを削除 ▼▼▼
        print("\n2. post_analysis_cache テーブルのデータを削除しています...")
        cur.execute("DELETE FROM post_analysis_cache;")
        print("✅ post_analysis_cache テーブルのデータを削除しました。")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("\nすべての関連データの削除が正常に完了しました。")
        print("アプリケーションを再起動して、タイムラインを再読み込みしてください。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    delete_cache_and_related_feedback()