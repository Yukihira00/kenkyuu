# database.py

import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
from pgvector.psycopg2 import register_vector

load_dotenv()
DB_NAME = os.getenv('POSTGRES_DB')
DB_USER = os.getenv('POSTGRES_USER')
DB_PASS = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('POSTGRES_HOST')

def get_connection():
    """データベースへの接続を取得し、vector型を登録する"""
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    register_vector(conn)
    return conn

def initialize_database():
    """データベースとテーブルを初期化する"""
    # ステップ1: 拡張機能を作成するための専用接続
    try:
        conn_init = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        cursor_init = conn_init.cursor()
        cursor_init.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn_init.commit()
        cursor_init.close()
        conn_init.close()
        print("✅ pgvector 拡張機能が有効化されました。")
    except Exception as e:
        print(f"⚠️ pgvector 拡張機能の有効化中にエラーが発生しました: {e}")
        return

    # ステップ2: 拡張機能が有効になった後、テーブルを作成するための通常の接続
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_did TEXT PRIMARY KEY, handle TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS hexaco_results (
        result_id SERIAL PRIMARY KEY, user_did TEXT NOT NULL,
        H REAL NOT NULL, E REAL NOT NULL, X REAL NOT NULL,
        A REAL NOT NULL, C REAL NOT NULL, O REAL NOT NULL,
        diagnosed_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )''')
    
    # ▼▼▼【修正】filter_strength列を追加 ▼▼▼
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filter_settings (
        setting_id SERIAL PRIMARY KEY, user_did TEXT NOT NULL UNIQUE,
        hidden_content_categories TEXT[] NOT NULL,
        auto_filter_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        similarity_filter_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        filter_strength INTEGER NOT NULL DEFAULT 2, -- 1:弱, 2:標準, 3:強
        updated_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS post_analysis_cache (
        post_uri TEXT PRIMARY KEY, content_category TEXT NOT NULL,
        expression_category TEXT NOT NULL, style_stance_category TEXT NOT NULL,
        embedding vector(384),
        analyzed_at TIMESTAMPTZ NOT NULL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS unpleasant_feedback (
        feedback_id SERIAL PRIMARY KEY, user_did TEXT NOT NULL, post_uri TEXT NOT NULL,
        reported_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did),
        FOREIGN KEY (post_uri) REFERENCES post_analysis_cache (post_uri)
    )''')

    # ▼▼▼【追加】フィルターへのフィードバックを保存するテーブルを追加 ▼▼▼
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filter_feedback (
        feedback_id SERIAL PRIMARY KEY,
        user_did TEXT NOT NULL,
        post_uri TEXT NOT NULL,
        filter_type TEXT NOT NULL, -- 'personality', 'similarity', 'manual'など
        feedback TEXT NOT NULL, -- 'correct', 'incorrect'
        created_at TIMESTAMPTZ NOT NULL,
        FOREIGN KEY (user_did) REFERENCES users (user_did)
    )''')


    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ PostgreSQLデータベース '{DB_NAME}' のテーブル初期化が完了しました。")


def add_unpleasant_feedback(user_did: str, post_uri: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute("SELECT 1 FROM unpleasant_feedback WHERE user_did = %s AND post_uri = %s", (user_did, post_uri))
    if cursor.fetchone():
        cursor.close(); conn.close(); return
    cursor.execute('INSERT INTO unpleasant_feedback (user_did, post_uri, reported_at) VALUES (%s, %s, %s)', (user_did, post_uri, now))
    conn.commit()
    cursor.close()
    conn.close()

def get_unpleasant_feedback_uris(user_did: str) -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT post_uri FROM unpleasant_feedback WHERE user_did = %s", (user_did,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return [result['post_uri'] for result in results]

def get_unpleasant_post_vectors(user_did: str) -> list[np.ndarray]:
    """指定されたユーザーが不快報告した投稿のベクトルリストを取得する"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
    SELECT cache.embedding
    FROM unpleasant_feedback AS feedback
    JOIN post_analysis_cache AS cache ON feedback.post_uri = cache.post_uri
    WHERE feedback.user_did = %s AND cache.embedding IS NOT NULL;
    """
    cursor.execute(query, (user_did,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return [result['embedding'] for result in results]

def add_or_update_hexaco_result(user_did: str, handle: str, scores: dict):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('INSERT INTO users (user_did, handle, created_at) VALUES (%s, %s, %s) ON CONFLICT (user_did) DO UPDATE SET handle = EXCLUDED.handle', (user_did, handle, now))
    cursor.execute('INSERT INTO hexaco_results (user_did, H, E, X, A, C, O, diagnosed_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', (user_did, scores['H'], scores['E'], scores['X'], scores['A'], scores['C'], scores['O'], now))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_result(user_did: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM hexaco_results WHERE user_did = %s ORDER BY diagnosed_at DESC LIMIT 1', (user_did,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result if result else None

def get_user_filter_settings(user_did: str):
    conn = get_connection()
    cursor = conn.cursor()
    # ▼▼▼【修正】filter_strength列を取得するように修正 ▼▼▼
    cursor.execute("SELECT hidden_content_categories, auto_filter_enabled, similarity_filter_enabled, filter_strength FROM filter_settings WHERE user_did = %s", (user_did,))
    settings = cursor.fetchone()
    cursor.close()
    conn.close()
    if settings: return settings
    # ▼▼▼【修正】デフォルト値にfilter_strengthを追加 ▼▼▼
    else: return {'hidden_content_categories': [], 'auto_filter_enabled': True, 'similarity_filter_enabled': True, 'filter_strength': 2}

# ▼▼▼【修正】関数シグネチャとSQL文を修正 ▼▼▼
def save_user_filter_settings(user_did: str, content: list[str], auto_filter: bool, similarity_filter: bool, filter_strength: int):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''
        INSERT INTO filter_settings (user_did, hidden_content_categories, auto_filter_enabled, similarity_filter_enabled, filter_strength, updated_at) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_did) DO UPDATE SET
            hidden_content_categories = EXCLUDED.hidden_content_categories, 
            auto_filter_enabled = EXCLUDED.auto_filter_enabled, 
            similarity_filter_enabled = EXCLUDED.similarity_filter_enabled,
            filter_strength = EXCLUDED.filter_strength,
            updated_at = EXCLUDED.updated_at
    ''', (user_did, content, auto_filter, similarity_filter, filter_strength, now))
    conn.commit()
    cursor.close()
    conn.close()

def get_cached_analysis_results(post_uris: list[str]) -> dict[str, dict]:
    if not post_uris: return {}
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join(['%s'] * len(post_uris))
    query = f"SELECT post_uri, content_category, expression_category, style_stance_category, embedding FROM post_analysis_cache WHERE post_uri IN ({placeholders})"
    cursor.execute(query, tuple(post_uris))
    cached_results = cursor.fetchall()
    cursor.close()
    conn.close()
    return {result['post_uri']: result for result in cached_results}

def save_analysis_results(post_uri: str, analysis_result: dict):
    if not analysis_result or 'embedding' not in analysis_result or analysis_result['embedding'] is None:
        return
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    content = analysis_result.get('content_category', '不明')
    expression = analysis_result.get('expression_category', '不明')
    style = analysis_result.get('style_stance_category', '不明')
    embedding = np.array(analysis_result['embedding'])
    cursor.execute('''
        INSERT INTO post_analysis_cache (post_uri, content_category, expression_category, style_stance_category, embedding, analyzed_at)
        VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (post_uri) DO NOTHING
    ''', (post_uri, content, expression, style, embedding, now))
    conn.commit()
    cursor.close()
    conn.close()

# ▼▼▼【追加】フィードバックを保存する関数を追加 ▼▼▼
def add_filter_feedback(user_did: str, post_uri: str, filter_type: str, feedback: str):
    """ユーザーからのフィルターフィードバックをデータベースに保存する"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute(
        'INSERT INTO filter_feedback (user_did, post_uri, filter_type, feedback, created_at) VALUES (%s, %s, %s, %s, %s)',
        (user_did, post_uri, filter_type, feedback, now)
    )
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == '__main__':
    initialize_database()