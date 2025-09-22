# update_schema_add_strength.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def update_schema():
    """filter_settingsテーブルにfilter_strength列を追加する"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        cur = conn.cursor()
        # 'filter_strength' 列が存在しない場合のみ追加する
        cur.execute("""
            ALTER TABLE filter_settings
            ADD COLUMN IF NOT EXISTS filter_strength INTEGER NOT NULL DEFAULT 2;
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ filter_settings テーブルのスキーマを正常に更新しました。'filter_strength'列が追加されました。")
    except Exception as e:
        print(f"スキーマの更新中にエラーが発生しました: {e}")

if __name__ == "__main__":
    update_schema()