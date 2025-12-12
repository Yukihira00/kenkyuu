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
    """アプリケーション用の接続を取得（pgvector登録付き）"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        # アプリでの利用時はpgvectorを登録する
        try:
            register_vector(conn)
        except Exception as e:
            print(f"⚠️ vector型の登録警告: {e}")
        return conn
    except Exception as e:
        print(f"❌ データベース接続エラー: {e}")
        raise e

def initialize_database():
    """データベースとテーブルを初期化する（DDL専用接続を使用）"""
    print("🚀 データベース初期化プロセスを開始します...")
    
    try:
        # 【修正点】get_connection()を使わず、素の接続を使う
        # これにより register_vector に起因するトランザクション問題を回避する
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST)
        conn.autocommit = True # エラー回避のため即座に自動コミットモードへ
        cursor = conn.cursor()

        print("🔧 pgvector拡張機能を確認中...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        except Exception as e:
            print(f"⚠️ 拡張機能スキップ（すでに存在する等）: {e}")

        print("🛠️ テーブルを作成中...")

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
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS filter_settings (
            setting_id SERIAL PRIMARY KEY, user_did TEXT NOT NULL UNIQUE,
            hidden_content_categories TEXT[] NOT NULL,
            auto_filter_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            similarity_filter_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            filter_strength INTEGER NOT NULL DEFAULT 2,
            similarity_threshold REAL NOT NULL DEFAULT 0.80,
            updated_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY (user_did) REFERENCES users (user_did)
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_analysis_cache (
            post_uri TEXT PRIMARY KEY, content_category TEXT NOT NULL,
            expression_category TEXT NOT NULL, style_stance_category TEXT NOT NULL,
            embedding vector(768),
            analyzed_at TIMESTAMPTZ NOT NULL
        )''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS unpleasant_feedback (
            feedback_id SERIAL PRIMARY KEY, user_did TEXT NOT NULL, post_uri TEXT NOT NULL,
            reported_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY (user_did) REFERENCES users (user_did),
            FOREIGN KEY (post_uri) REFERENCES post_analysis_cache (post_uri)
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS filter_feedback (
            feedback_id SERIAL PRIMARY KEY,
            user_did TEXT NOT NULL,
            post_uri TEXT NOT NULL,
            filter_type TEXT NOT NULL,
            feedback TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            FOREIGN KEY (user_did) REFERENCES users (user_did)
        )''')

        cursor.close()
        conn.close()
        print("✅ 全テーブルの作成確認が完了しました。")
        
    except Exception as e:
        print(f"❌ テーブル作成中に致命的なエラーが発生: {e}")

# --- 以下は変更なし ---

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
    cursor.execute("SELECT hidden_content_categories, auto_filter_enabled, similarity_filter_enabled, filter_strength, similarity_threshold FROM filter_settings WHERE user_did = %s", (user_did,))
    settings = cursor.fetchone()
    cursor.close()
    conn.close()
    if settings: return settings
    else: return {'hidden_content_categories': [], 'auto_filter_enabled': True, 'similarity_filter_enabled': True, 'filter_strength': 2, 'similarity_threshold': 0.80}

def save_user_filter_settings(user_did: str, content: list[str], auto_filter: bool, similarity_filter: bool, filter_strength: int, similarity_threshold: float):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now()
    cursor.execute('''
        INSERT INTO filter_settings (user_did, hidden_content_categories, auto_filter_enabled, similarity_filter_enabled, filter_strength, similarity_threshold, updated_at) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_did) DO UPDATE SET
            hidden_content_categories = EXCLUDED.hidden_content_categories, 
            auto_filter_enabled = EXCLUDED.auto_filter_enabled, 
            similarity_filter_enabled = EXCLUDED.similarity_filter_enabled,
            filter_strength = EXCLUDED.filter_strength,
            similarity_threshold = EXCLUDED.similarity_threshold,
            updated_at = EXCLUDED.updated_at
    ''', (user_did, content, auto_filter, similarity_filter, filter_strength, similarity_threshold, now))
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

def add_filter_feedback(user_did: str, post_uri: str, filter_type: str, feedback: str):
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