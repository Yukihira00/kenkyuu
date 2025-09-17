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
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 3軸のカテゴリ定義 ---

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

# 【軸2】表現カテゴリ（ポジティブ/ネガティブ）
EXPRESSION_CATEGORIES = [
    "肯定的・中立的",
    "否定的・批判的",
    "ショッキングな表現"
]

# 【軸3】スタイル・スタンスカテゴリ（ユーザーの指示に基づき刷新）
STYLE_STANCE_CATEGORIES = [
    # H (Honesty-Humility)
    "大げさな表現・釣りタイトル", "自慢話", "ステマ",
    "教訓めいた投稿", "過度なへりくだり・自虐",
    # E (Emotionality)
    "感傷的なポエム", "感情的な共感を求める投稿",
    # X (eXtraversion)
    "専門的な長文解説", "内省的・静的なトーン",
    "派手・注目目的の投稿", "大人数での交流を促す投稿",
    # A (Agreeableness)
    "批判・論争的", "対立を煽る投稿",
    "建前・本音が見えない投稿", "当たり障りのない意見",
    # C (Conscientiousness)
    "不正確・論理破綻", "誤字脱字が多い",
    "細かいルール・手順の説明", "緻密なデータ・分析",
    # O (Openness to Experience)
    "平凡な日常報告", "ありきたりな内容",
    "抽象的・アート系", "突飛なアイデア",
    # General
    "その他"
]


# プロンプト用にカテゴリのリストを平坦化
flat_content_categories = [item for sublist in CONTENT_CATEGORIES.values() for item in sublist]

# -----------------------------------------------------------------

def analyze_posts_batch(texts: list[str]):
    """
    複数の投稿テキストをGemini APIに送信し、3つの軸で分析して返す。
    """
    if not API_KEY:
        print("エラー: GEMINI_API_KEYが設定されていません。")
        return None

    # 分析失敗時に返すエラー用の辞書
    error_result = {
        "content_category": "分析失敗",
        "expression_category": "分析失敗",
        "style_stance_category": "分析失敗"
    }

    formatted_texts = []
    for i, text in enumerate(texts):
        formatted_texts.append(f"投稿{i+1}:\n---\n{text}\n---")
    
    prompt = f"""
    以下のSNS投稿リスト（{len(texts)}件）を分析し、それぞれの投稿について3つの軸で最も適切なカテゴリを1つずつ選択してください。
    回答は、JSONオブジェクトのリスト形式で、投稿の順番通りに出力してください。

    # 分析の軸:
    1. content_category: 投稿の主要な内容・トピック
    2. expression_category: 投稿全体の感情的な表現
    3. style_stance_category: 投稿の文体や書き手のスタンス（最も顕著な特徴を1つ選択）

    # 制約:
    - 各カテゴリは必ず以下のリストから選択してください:
      - "content_category": {flat_content_categories}
      - "expression_category": {EXPRESSION_CATEGORIES}
      - "style_stance_category": {STYLE_STANCE_CATEGORIES}
    - 回答はJSONオブジェクトのリストのみとし、説明文などは一切含めないでください。
    - 各JSONオブジェクトには "content_category", "expression_category", "style_stance_category" の3つのキーを必ず含めてください。

    # 投稿リスト:
    {"\n".join(formatted_texts)}

    # 出力形式 (JSONリスト):
    [
      {{
        "content_category": "（投稿1のコンテンツカテゴリ）",
        "expression_category": "（投稿1の表現カテゴリ）",
        "style_stance_category": "（投稿1のスタイル・スタンスカテゴリ）"
      }},
      ...
    ]
    """

    try:
        response = model.generate_content(prompt)
        
        json_text = response.text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:-3].strip()
        
        analysis_results = json.loads(json_text)
        
        if isinstance(analysis_results, list) and len(analysis_results) == len(texts):
            if all(isinstance(r, dict) and "content_category" in r for r in analysis_results):
                 return analysis_results
        
        print(f"エラー: LLMからのレスポンス形式が不正、または結果の件数や内容が一致しません。")
        return [error_result] * len(texts)

    except Exception as e:
        print(f"LLMでの分析中にエラーが発生しました: {e}")
        return [error_result] * len(texts)


if __name__ == '__main__':
    print("--- LLM分析テスト ---")
    
    sample_posts = [
        "【衝撃】この方法を使えば、あなたも1ヶ月で10kg痩せられる！", 
        "ついに憧れのタワマン最上階に引っ越しました！夜景が最高すぎる…",
        "このサプリ、本当に効果あるの？って聞かれるけど、使ってみたらマジで人生変わるよ（個人の感想です）",
        "「情けは人のためならず」は情けをかけると巡り巡って自分に返ってくる、という意味。間違って覚えてる人多すぎ。",
        "私なんて何をやってもダメダメだ…",
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