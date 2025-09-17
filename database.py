# database.py
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

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_did TEXT PRIMARY KEY,
        handle TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hexaco_results (
        result_id SERIAL PRIMARY KEY,
        user_did TEXT NOT NULL,
        H REAL NOT NULL, E REAL NOT NULL, X REAL NOT NULL,
        A REAL NOT NULL, C REAL NOT NULL, O REAL NOT NULL,
        diagnosed_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filter_settings (
        setting_id SERIAL PRIMARY KEY,
        user_did TEXT NOT NULL UNIQUE,
        hidden_content_categories TEXT[] NOT NULL,
        auto_filter_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        updated_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS post_analysis_cache (
        post_uri TEXT PRIMARY KEY,
        content_category TEXT NOT NULL,
        expression_category TEXT NOT NULL,
        style_stance_category TEXT NOT NULL,
        analyzed_at TIMESTAMPTZ NOT NULL
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
        return result
    else:
        return None

def get_user_filter_settings(user_did: str):
    """指定されたユーザーのフィルター設定を取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT hidden_content_categories, auto_filter_enabled FROM filter_settings WHERE user_did = %s", (user_did,))
    settings = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if settings:
        return settings
    else:
        return {
            'hidden_content_categories': [],
            'auto_filter_enabled': True
        }

def save_user_filter_settings(user_did: str, content: list[str], auto_filter: bool):
    """ユーザーのフィルター設定を保存または更新する"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    cursor.execute('''
        INSERT INTO filter_settings (user_did, hidden_content_categories, auto_filter_enabled, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_did) DO UPDATE SET
            hidden_content_categories = EXCLUDED.hidden_content_categories,
            auto_filter_enabled = EXCLUDED.auto_filter_enabled,
            updated_at = EXCLUDED.updated_at
    ''', (user_did, content, auto_filter, now))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ ユーザー (did: ...{user_did[-6:]}) のフィルター設定を保存しました。")

def get_cached_analysis_results(post_uris: list[str]) -> dict[str, dict]:
    """指定された投稿URIのリストについて、キャッシュ済みの分析結果を辞書で返す"""
    if not post_uris:
        return {}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    placeholders = ','.join(['%s'] * len(post_uris))
    query = f"SELECT post_uri, content_category, expression_category, style_stance_category FROM post_analysis_cache WHERE post_uri IN ({placeholders})"
    
    cursor.execute(query, tuple(post_uris))
    cached_results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {result['post_uri']: result for result in cached_results}

def save_analysis_results(post_uri: str, analysis_result: dict):
    """単一の分析結果をキャッシュテーブルに保存する"""
    if not analysis_result:
        return

    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()

    # .get()のデフォルト値を「N/A」から「不明」に変更し、AIからの意図しない応答に備える
    content = analysis_result.get('content_category', '不明')
    expression = analysis_result.get('expression_category', '不明')
    style = analysis_result.get('style_stance_category', '不明')

    cursor.execute('''
        INSERT INTO post_analysis_cache (post_uri, content_category, expression_category, style_stance_category, analyzed_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (post_uri) DO NOTHING
    ''', (
        post_uri,
        content,
        expression,
        style,
        now
    ))

    conn.commit()
    cursor.close()
    conn.close()

if __name__ == '__main__':
    initialize_database()