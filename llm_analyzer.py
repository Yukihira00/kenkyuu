# llm_analyzer.py
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv(encoding='utf-8')
API_KEY = os.getenv('GEMINI_API_KEY')

# APIキーを使ってGeminiを設定
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash-lite')

# --- 3軸のカテゴリ定義を修正 ---

# 【軸1】コンテンツカテゴリ（内容・トピック別）
CONTENT_CATEGORIES = {
    "暮らし (Life & Living)": [
        "食事・料理", "住まい・暮らし", "お出かけ・旅行", "健康・ウェルネス",
        "美容・ファッション", "買い物・消費", "家族・育児", "ペット"
    ],
    "趣味 (Hobbies & Interests)": [
        "カルチャー（映画・音楽等）", "ゲーム", "スポーツ", "創作・表現",
        "アウトドア", "学び・探求"
    ],
    "仕事と社会 (Work & Society)": [
        "仕事・キャリア", "学習・スキル", "テクノロジー", "経済・金融",
        "社会・時事", "人間関係"
    ]
}

# ★★★ 不要なカテゴリ定義を削除 ★★★

# プロンプト用にカテゴリのリストを平坦化
flat_content_categories = [item for sublist in CONTENT_CATEGORIES.values() for item in sublist]

# -----------------------------------------------------------------

def analyze_posts_batch(texts: list[str]):
    """
    複数の投稿テキストをGemini APIに送信し、コンテンツカテゴリを分析して返す。
    """
    if not API_KEY:
        print("エラー: GEMINI_API_KEYが設定されていません。")
        return None

    # 各投稿を連番と区切り線で整形
    formatted_texts = []
    for i, text in enumerate(texts):
        formatted_texts.append(f"投稿{i+1}:\n---\n{text}\n---")
    
    # ★★★ LLMへの指示（プロンプト）を修正 ★★★
    prompt = f"""
    以下のSNS投稿リスト（{len(texts)}件）を分析し、それぞれの投稿について最も適切なコンテンツカテゴリを1つ選択してください。
    回答は、JSONオブジェクトのリスト形式で、投稿の順番通りに出力してください。

    # 分析の軸:
    1. content_category: 投稿の主要な内容・トピック

    # 制約:
    - 「content_category」は必ず以下のリストから選択してください: {flat_content_categories}
    - 回答はJSONオブジェクトのリストのみとし、説明文などは一切含めないでください。
    - 各JSONオブジェクトには "content_category" のキーを必ず含めてください。

    # 投稿リスト:
    {"\n".join(formatted_texts)}

    # 出力形式 (JSONリスト):
    [
      {{
        "content_category": "（投稿1のコンテンツカテゴリ）"
      }},
      {{
        "content_category": "（投稿2のコンテンツカテゴリ）"
      }},
      ...
    ]
    """

    try:
        # LLMにリクエストを送信
        response = model.generate_content(prompt)
        
        # レスポンスからJSON部分を抽出
        json_text = response.text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:-3].strip()
        
        analysis_results = json.loads(json_text)
        
        # 結果がリスト形式であり、件数が元の投稿数と一致するか確認
        if isinstance(analysis_results, list) and len(analysis_results) == len(texts):
            return analysis_results
        else:
            print(f"エラー: LLMからのレスポンス形式が不正、または結果の件数が一致しません。")
            return [None] * len(texts) # 元の投稿数に合わせてNoneのリストを返す

    except Exception as e:
        print(f"LLMでの分析中にエラーが発生しました: {e}")
        return [None] * len(texts) # エラー時もNoneのリストを返す


# (テスト用のコードは変更なし)
if __name__ == '__main__':
    print("--- LLM分析テスト ---")
    
    sample_posts = [
        "新しいPC買った！作業効率が爆上がりして最高！ #ガジェット",
        "今日の会議、内容が薄いのに長くて本当に時間の無駄だったな...",
        "政治家の汚職ニュース、もう聞き飽きた。この国はどうなってるんだ？",
        "近所のラーメン屋、今まで食べた中で一番美味しかった。店主さんありがとう！",
        "この週末、3年ぶりに開催される地元のお祭りにボランティアとして参加します！楽しみ！"
    ]
    
    print(f"\n{len(sample_posts)}件の投稿をまとめて分析します。")
    results = analyze_posts_batch(sample_posts)
    
    if results:
        for i, (post, result) in enumerate(zip(sample_posts, results)):
            print(f"\n投稿{i+1}: '{post}'")
            if result:
                print(f"  -> 分析結果: {result}")
            else:
                print("  -> 分析に失敗しました。")