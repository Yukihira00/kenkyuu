import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def delete_all_results():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM hexaco_results;")
    conn.commit()
    cur.close()
    conn.close()
    print("hexaco_resultsテーブルの全データを削除しました。")

if __name__ == "__main__":
    delete_all_results()