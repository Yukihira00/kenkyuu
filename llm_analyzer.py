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

# --- 新しい3軸のカテゴリ定義 ---

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

# 【軸2】表現カテゴリ（トーン・感情・目的別）
EXPRESSION_CATEGORIES = {
    "ポジティブ": ["喜び", "感謝", "感動", "祝福", "愛情", "賞賛", "興奮", "期待", "安らぎ", "癒やし"],
    "ネガティブ": ["怒り", "不満", "悲しみ", "落胆", "不安", "心配", "後悔", "嫉妬", "軽蔑", "疲労"],
    "ニュートラル": ["驚き", "発見", "懐かしさ", "共感", "寂しさ", "静かな気持ち"],
    "情報共有・記録": ["ノウハウ・TIPS共有", "レビュー・評価", "まとめ・リスト", "体験談・レポート", "進捗報告"],
    "意見・思考": ["意見表明", "主張", "考察・分析", "批評・問題提起", "自己内省", "決意表明"],
    "コミュニケーション": ["質問・相談", "回答・返信", "呼びかけ・問いかけ", "雑談・つぶやき"],
    "宣伝・告知": ["イベント告知", "商品・作品の宣伝", "自己紹介・PR", "募集"]
}


# 【軸3】文体・スタンスカテゴリ（文章の書き方別）
STYLE_STANCE_CATEGORIES = {
    "対人スタンス (Interpersonal Stance)": [
        "上から目線 / 教示的", "自慢 / 誇示的", "皮肉 / 嫌味", "攻撃的 / 批判的",
        "挑発的 / 扇動的", "謙虚 / 丁寧", "共感的 / 寄り添い", "フレンドリー / 親近感"
    ],
    "自己表現スタイル (Self-Expression Style)": [
        "自虐的", "客観的 / 分析的", "断定的 / 主張的", "控えめ / 曖昧",
        "論理的 / 構造的", "感情的 / 情熱的"
    ],
    "文体の特徴 (Writing Characteristics)": [
        "ポエム / 詩的", "ユーモラス / 面白おかしい", "簡潔 / 箇条書き",
        "口語体 / 話し言葉", "ですます調 / 敬体", "だである調 / 常体"
    ]
}

# プロンプト用にカテゴリのリストを平坦化
flat_content_categories = [item for sublist in CONTENT_CATEGORIES.values() for item in sublist]
flat_expression_categories = [item for sublist in EXPRESSION_CATEGORIES.values() for item in sublist]
flat_style_stance_categories = [item for sublist in STYLE_STANCE_CATEGORIES.values() for item in sublist]

# -----------------------------------------------------------------

def analyze_post_text(text: str):
    """
    投稿テキストをGemini APIに送信し、3つの軸でカテゴリを分析して返す。
    """
    if not API_KEY:
        print("エラー: GEMINI_API_KEYが設定されていません。")
        return None

    # LLMへの指示（プロンプト）を作成
    prompt = f"""
    以下のSNS投稿を分析し、3つの軸それぞれについて最も適切なカテゴリを1つだけ選択し、JSON形式で回答してください。

    # 分析の軸:
    1. content_category: 投稿の主要な内容・トピック
    2. expression_category: 投稿に込められた感情、目的、スタイル
    3. style_stance_category: 文章の書き方や他者へのスタンス

    # 制約:
    - 「content_category」は必ず以下のリストから選択してください: {flat_content_categories}
    - 「expression_category」は必ず以下のリストから選択してください: {flat_expression_categories}
    - 「style_stance_category」は必ず以下のリストから選択してください: {flat_style_stance_categories}
    - 回答はJSONオブジェクトのみとし、説明文などは一切含めないでください。

    # 投稿テキスト:
    "{text}"

    # 出力形式:
    {{
      "content_category": "（選択したコンテンツカテゴリ）",
      "expression_category": "（選択した表現カテゴリ）",
      "style_stance_category": "（選択した文体・スタンスカテゴリ）"
    }}
    """

    try:
        # LLMにリクエストを送信
        response = model.generate_content(prompt)
        
        # レスポンスからJSON部分を抽出
        json_text = response.text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:-3].strip()
        
        analysis_result = json.loads(json_text)
        
        # 想定したキーが存在するかチェック
        if "content_category" in analysis_result and "expression_category" in analysis_result and "style_stance_category" in analysis_result:
            return analysis_result
        else:
            print(f"エラー: LLMからのレスポンス形式が不正です。Response: {response.text}")
            return None

    except Exception as e:
        print(f"LLMでの分析中にエラーが発生しました: {e}")
        return None

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
    
    for i, post in enumerate(sample_posts, 1):
        print(f"\n投稿{i}: '{post}'")
        result = analyze_post_text(post)
        if result:
            print(f"  -> 分析結果: {result}")