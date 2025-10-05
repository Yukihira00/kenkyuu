# feedback_analyzer.py
import database
from collections import defaultdict
import pandas as pd

def analyze_feedback():
    """
    データベースからフィルターのフィードバックを取得し、
    どのフィルターが、どのカテゴリの投稿を、どの程度間違えているかを集計して表示する。
    """
    try:
        conn = database.get_connection()
        # post_analysis_cache と filter_feedback を結合して必要な情報を取得
        query = """
        SELECT
            f.filter_type,
            f.feedback,
            p.content_category,
            p.expression_category,
            p.style_stance_category,
            p.post_uri
        FROM
            filter_feedback AS f
        JOIN
            post_analysis_cache AS p ON f.post_uri = p.post_uri;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            print("フィードバックデータがありません。")
            return

        print("--- フィルターフィードバック分析結果 ---")

        # フィルタータイプごとの正解・不正解率
        print("\n▼ フィルタータイプごとの正解・不正解率")
        accuracy_by_type = df.groupby('filter_type')['feedback'].value_counts(normalize=True).unstack().fillna(0)
        print(accuracy_by_type)

        # 「表示して良い(incorrect)」と判断された投稿の分析
        incorrect_df = df[df['feedback'] == 'incorrect']
        if not incorrect_df.empty:
            print("\n▼《問題分析》「表示して良い(incorrect)」と判断された投稿の内訳")
            
            for filter_type in incorrect_df['filter_type'].unique():
                print(f"\n--- フィルタータイプ: {filter_type} ---")
                
                type_df = incorrect_df[incorrect_df['filter_type'] == filter_type]
                
                print("【コンテンツカテゴリ】")
                print(type_df['content_category'].value_counts().to_string())
                
                print("\n【表現カテゴリ】")
                print(type_df['expression_category'].value_counts().to_string())
                
                print("\n【スタイル・スタンスカテゴリ】")
                print(type_df['style_stance_category'].value_counts().to_string())
        else:
            print("\n▼「表示して良い(incorrect)」と判断された投稿はありませんでした。")


    except Exception as e:
        print(f"フィードバックの分析中にエラーが発生しました: {e}")

if __name__ == "__main__":
    analyze_feedback()