import database

def calculate_performance():
    print("データベースを集計中...\n")
    try:
        conn = database.get_connection()
        cursor = conn.cursor()

        # 1. 漏れ（見たくないものを見せてしまった）
        # AS count で名前を付け、['count'] で取り出します
        cursor.execute("SELECT COUNT(*) as count FROM unpleasant_feedback")
        result = cursor.fetchone()
        false_negatives = result['count'] if result else 0

        # 2. 過剰（見たいものを隠してしまった）
        cursor.execute("SELECT COUNT(*) as count FROM filter_feedback WHERE feedback = 'incorrect'")
        result = cursor.fetchone()
        false_positives = result['count'] if result else 0

        # 3. 正解（正しく隠した）
        cursor.execute("SELECT COUNT(*) as count FROM filter_feedback WHERE feedback = 'correct'")
        result = cursor.fetchone()
        true_positives = result['count'] if result else 0

        conn.close()

        # --- 統計指標の計算 ---
        # フィルターが作動した総数（隠した数）
        total_hidden = true_positives + false_positives
        
        # 実際に不快だった投稿の総数（隠せたもの + 漏れたもの）
        total_actually_unpleasant = true_positives + false_negatives

        print("【集計結果】")
        print(f"❌ 見たいものを隠してしまった (過剰/False Positive) : {false_positives} 件")
        print(f"⚠️ 見たくないものを見せてしまった (漏れ/False Negative): {false_negatives} 件")
        print(f"✅ 正しく隠した (正解/True Positive)                 : {true_positives} 件")
        print("-" * 50)

        # 1. 適合率 (Precision)
        if total_hidden > 0:
            precision = (true_positives / total_hidden) * 100
            print(f"■ 適合率 (Precision): {precision:.1f}%")
            print(f"   意味: フィルターが作動したとき、それが正解である確率")
        else:
            print("■ 適合率 (Precision): データなし（フィルター作動なし）")

        # 2. 再現率 (Recall)
        if total_actually_unpleasant > 0:
            recall = (true_positives / total_actually_unpleasant) * 100
            print(f"\n■ 再現率 (Recall)   : {recall:.1f}%")
            print(f"   意味: 本当に不快な投稿のうち、何％をブロックできたか")
        else:
            print("\n■ 再現率 (Recall)   : データなし（不快な投稿ゼロ）")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    calculate_performance()