# delete_unpleasant_feedback.py (ファイル名を変更せず、この内容に更新)
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def delete_dependent_tables():
    """依存関係のあるテーブルを正しい順序で削除する"""
    # 外部キー制約のため、削除する順序が重要です
    tables_to_delete = [
        "filter_feedback",
        "unpleasant_feedback",
        "post_analysis_cache"
    ]
    
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST
        )
        cur = conn.cursor()
        
        for table in tables_to_delete:
            print(f"Deleting table: {table}...")
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            print(f"✅ Table {table} deleted successfully.")
            
        conn.commit()
        cur.close()
        conn.close()
        print("\nAll dependent tables have been successfully deleted.")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    delete_dependent_tables()