import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()
# 環境変数からデータベース接続情報を取得
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def get_connection():
    """データベースへの接続を取得する"""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        cursor_factory=psycopg2.extras.RealDictCursor  # 結果を辞書形式で取得する設定
    )
    return conn

def initialize_database():
    """データベースとテーブルを初期化（存在しない場合のみ作成）する"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. users テーブルの作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_did TEXT PRIMARY KEY,
        handle TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    ''')

    # 2. hexaco_results テーブルの作成
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hexaco_results (
        result_id SERIAL PRIMARY KEY,
        user_did TEXT NOT NULL,
        H REAL NOT NULL,
        E REAL NOT NULL,
        X REAL NOT NULL,
        A REAL NOT NULL,
        C REAL NOT NULL,
        O REAL NOT NULL,
        diagnosed_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )
    ''')
    
    # 3. filter_settings テーブルの作成 (★ここが重要★)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filter_settings (
        setting_id SERIAL PRIMARY KEY,
        user_did TEXT NOT NULL UNIQUE,
        hidden_topics TEXT[] NOT NULL,
        hidden_tones TEXT[] NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )
    ''')

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ PostgreSQLデータベース '{DB_NAME}' の初期化が完了しました。")

def add_or_update_hexaco_result(user_did: str, handle: str, scores: dict):
    """ユーザー情報とHEXACO診断結果をデータベースに追加または更新する"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()

    cursor.execute('''
    INSERT INTO users (user_did, handle, created_at)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_did) DO UPDATE SET
        handle = EXCLUDED.handle
    ''', (user_did, handle, now))

    cursor.execute('''
    INSERT INTO hexaco_results (user_did, H, E, X, A, C, O, diagnosed_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (user_did, scores['H'], scores['E'], scores['X'], scores['A'], scores['C'], scores['O'], now))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ ユーザー '{handle}' の診断結果をPostgreSQLに保存しました。")

def get_user_result(user_did: str):
    """指定されたユーザーの最新のHEXACO診断結果を取得する"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT * FROM hexaco_results
    WHERE user_did = %s
    ORDER BY diagnosed_at DESC
    LIMIT 1
    ''', (user_did,))

    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        print(f"🔍 ユーザー (did: ...{user_did[-6:]}) の診断結果が見つかりました。")
        return result
    else:
        print(f"⚠️ ユーザー (did: ...{user_did[-6:]}) の診断結果はまだありません。")
        return None

def get_user_filter_settings(user_did: str):
    """指定されたユーザーのフィルター設定を取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT hidden_topics, hidden_tones FROM filter_settings WHERE user_did = %s", (user_did,))
    settings = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if settings:
        return settings
    else:
        return {'hidden_topics': [], 'hidden_tones': []}

def save_user_filter_settings(user_did: str, topics: list[str], tones: list[str]):
    """ユーザーのフィルター設定を保存または更新する"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    cursor.execute('''
        INSERT INTO filter_settings (user_did, hidden_topics, hidden_tones, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_did) DO UPDATE SET
            hidden_topics = EXCLUDED.hidden_topics,
            hidden_tones = EXCLUDED.hidden_tones,
            updated_at = EXCLUDED.updated_at
    ''', (user_did, topics, tones, now))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ ユーザー (did: ...{user_did[-6:]}) のフィルター設定を保存しました。")

if __name__ == '__main__':
    initialize_database()
    print("\n--- データ保存テスト ---")
    dummy_scores = {'H': 3.0, 'E': 1.0, 'X': 2.2, 'A': 3.8, 'C': 1.8, 'O': 3.0}
    dummy_did = 'did:plc:xxxxxxxxxxxxxxxxx'
    dummy_handle = 'testuser.bsky.social'
    add_or_update_hexaco_result(dummy_did, dummy_handle, dummy_scores)
    print("\n--- データ取得テスト ---")
    saved_result = get_user_result(dummy_did)
    if saved_result:
        print("取得したスコア:")
        print(f"  H: {saved_result['h']}, E: {saved_result['e']}, X: {saved_result['x']}")
        print(f"  A: {saved_result['a']}, C: {saved_result['c']}, O: {saved_result['o']}")
    print("\n--- 存在しないユーザーのテスト ---")
    get_user_result('did:plc:not-exist-user')