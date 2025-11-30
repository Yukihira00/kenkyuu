import database
import csv
import os

def simple_export():
    print("データベースに接続中...")
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
    except Exception as e:
        print(f"❌ 接続エラー: {e}")
        return

    # ---------------------------------------------------------
    # 1. フィルター評価テーブル (filter_feedback)
    # ---------------------------------------------------------
    print("\n--- 1. filter_feedback テーブルの取得 ---")
    
    # 複雑なJOINや日本語エイリアスを使わず、まずは生データを取得
    query = """
    SELECT 
        f.created_at,
        f.user_did,
        f.filter_type,
        f.feedback,
        p.content_category,
        p.expression_category,
        p.style_stance_category,
        f.post_uri
    FROM filter_feedback f
    LEFT JOIN post_analysis_cache p ON f.post_uri = p.post_uri
    ORDER BY f.created_at DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall() # 辞書型ではなくタプルやリストで返ってくる場合もあるので注意
        
        # データの件数確認
        print(f"取得できたデータ件数: {len(rows)} 件")

        if len(rows) > 0:
            # 念のため、最初の1件を画面に表示して中身チェック
            print("▼ データの先頭サンプル（画面表示用）:")
            first_row = rows[0]
            # 辞書型(RealDictCursor)の場合は .values() で値を取り出す
            if isinstance(first_row, dict):
                print(list(first_row.values()))
                headers = list(first_row.keys())
                data_to_write = [row.values() for row in rows]
            else:
                print(first_row)
                # カラム名を取得
                headers = [desc[0] for desc in cursor.description]
                data_to_write = rows

            # CSV書き出し
            filename = "simple_filter_feedback.csv"
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers) # ヘッダー書き込み
                writer.writerows(data_to_write) # データ全行書き込み
            
            print(f"✅ CSV保存完了: {filename}")
        else:
            print("⚠️ データが空です。")

    except Exception as e:
        print(f"❌ エラー発生: {e}")

    # ---------------------------------------------------------
    # 2. 不快報告テーブル (unpleasant_feedback)
    # ---------------------------------------------------------
    print("\n--- 2. unpleasant_feedback テーブルの取得 ---")
    query_u = """
    SELECT 
        u.reported_at,
        u.user_did,
        p.content_category,
        p.expression_category,
        u.post_uri
    FROM unpleasant_feedback u
    LEFT JOIN post_analysis_cache p ON u.post_uri = p.post_uri
    ORDER BY u.reported_at DESC;
    """
    try:
        cursor.execute(query_u)
        rows = cursor.fetchall()
        print(f"取得できたデータ件数: {len(rows)} 件")

        if len(rows) > 0:
            if isinstance(rows[0], dict):
                headers = list(rows[0].keys())
                data_to_write = [row.values() for row in rows]
            else:
                headers = [desc[0] for desc in cursor.description]
                data_to_write = rows

            filename_u = "simple_unpleasant_feedback.csv"
            with open(filename_u, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data_to_write)
            print(f"✅ CSV保存完了: {filename_u}")
            
    except Exception as e:
        print(f"❌ エラー発生: {e}")

    cursor.close()
    conn.close()
    print("\n全処理完了。")

if __name__ == "__main__":
    simple_export()