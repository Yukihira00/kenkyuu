import os
import psycopg2
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def delete_table():
    """filter_settingsテーブルを削除する"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST
        )
        cursor = conn.cursor()
        
        # テーブルを削除するSQLクエリを実行
        cursor.execute("DROP TABLE IF EXISTS filter_settings;")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ filter_settings テーブルを正常に削除しました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    delete_table()