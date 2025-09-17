import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def update_schema():
    """filter_settingsテーブルから不要な列を削除する"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        cur = conn.cursor()
        # 'learning_filter_enabled' 列が存在すれば削除する
        cur.execute("""
            ALTER TABLE filter_settings 
            DROP COLUMN IF EXISTS learning_filter_enabled;
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ filter_settings テーブルのスキーマを正常に更新しました。")
    except Exception as e:
        print(f"スキーマの更新中にエラーが発生しました: {e}")

if __name__ == "__main__":
    update_schema()