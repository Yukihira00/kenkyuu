import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def delete_unpleasant_feedback():
    """unpleasant_feedbackテーブルの全データを削除する"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        cur = conn.cursor()
        cur.execute("DELETE FROM unpleasant_feedback;")
        conn.commit()
        cur.close()
        conn.close()
        print("✅ unpleasant_feedback テーブルの全データを正常に削除しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    delete_unpleasant_feedback()