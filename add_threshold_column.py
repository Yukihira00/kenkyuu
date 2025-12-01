import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def add_column():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST')
        )
        cursor = conn.cursor()
        
        # similarity_thresholdカラムを追加 (デフォルトは0.80)
        cursor.execute("""
        ALTER TABLE filter_settings 
        ADD COLUMN IF NOT EXISTS similarity_threshold REAL NOT NULL DEFAULT 0.80;
        """)
        
        conn.commit()
        print("✅ カラム 'similarity_threshold' を追加しました。")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    add_column()