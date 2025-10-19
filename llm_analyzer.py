# llm_analyzer.py
import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv(encoding='utf-8')
API_KEY = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
embedding_model = SentenceTransformer('all-mpnet-base-v2')

# --- カテゴリ定義 (ユーザー提供の資料に基づいて変更) ---

# 1. content_category: Yahoo!知恵袋のカテゴリをベース
# (注: カテゴリが膨大なため、主要な大カテゴリと中カテゴリを抜粋・整理しています)
CONTENT_CATEGORIES = {
    "エンターテインメント・趣味": ["芸能人", "テレビ、ラジオ", "音楽", "映画", "アニメ、コミック", "ゲーム", "趣味", "おもちゃ", "本、雑誌", "占い、超常現象"],
    "暮らし・生活": ["料理、レシピ", "家事", "住宅", "日用品、生活雑貨", "ショッピング", "法律、消費者問題", "公共施設、役所", "郵便、宅配", "ペット", "園芸、ガーデニング", "海外生活"],
    "健康・美容・ファッション": ["健康、病気、病院", "ダイエット、フィットネス", "コスメ、美容", "ファッション", "メンタルヘルス", "性の悩み、相談"],
    "人間関係・マナー": ["マナー、冠婚葬祭", "恋愛相談、人間関係の悩み", "生き方、人生相談"],
    "子育て・学校": ["子育て、出産", "幼児教育、幼稚園、保育園", "小・中学校、高校", "大学、短大、大学院", "留学、ホームステイ", "受験、進学"],
    "テクノロジー": ["インターネット、通信", "スマホアプリ", "コミュニケーションサービス", "動画サービス", "スマートデバイス、PC、家電", "OS", "ソフトウェア", "プログラミング", "データベース", "ネットワーク技術", "セキュリティ"],
    "学問・サイエンス": ["言葉、語学", "生物、動物、植物", "歴史", "芸術、文学、哲学", "サイエンス", "数学", "天気、天文、宇宙", "一般教養"],
    "ビジネス・経済": ["企業と経営", "株と経済", "税金、年金", "保険", "家計、貯金", "決済、ポイントサービス", "職業とキャリア", "就職、転職", "労働問題、働き方"],
    "社会・スポーツ・旅行": ["ニュース、政治、国際情勢", "災害", "エネルギー、資源", "スポーツ", "自動車", "バイク", "アウトドア", "自転車、サイクリング", "地域、旅行、お出かけ"],
    "その他": ["雑談", "アダルト", "ギャンブル"]
}

# 2. expression_category: 27種類の感情分類をベース
EXPRESSION_CATEGORIES = [
    "敬服", "崇拝", "称賛", "娯楽", "焦慮", "畏敬", "当惑", "飽きる", "冷静", "困惑",
    "渇望", "嫌悪", "苦しみの共感", "夢中", "嫉妬", "興奮", "恐れ", "痛恨", "面白さ",
    "喜び", "懐旧", "ロマンチック", "悲しみ", "好感", "性欲", "同情", "満足", "その他・分類不能"
]

# 3. style_stance_category: 「クソリプ」の分類をベース (不快な投稿の検出を強化)
STYLE_STANCE_CATEGORIES = [
    # 身体的不安
    "セクハラ", "脅迫",
    # 精神的不安
    "上から目線", "うざいアドバイス", "マジレス", "難癖（曲解）", "全否定", "煽り", "侮辱",
    # 社会的不安
    "身内ディス",
    # 認知的不安
    "意味不明", "誤解",
    # 時間的不安
    "愚問", "自分語り", "個人の感想", "すべり", "自己中",
    
    # ▼▼▼ 注: 以下は中立・ポジティブな投稿を分類するために追加したカテゴリです ▼▼▼
    "一般的な意見・感想", "有益な情報提供", "質問・疑問", "挨拶・日常会話", "感謝・ポジティブな反応", "その他"
]

flat_content_categories = [item for sublist in CONTENT_CATEGORIES.values() for item in sublist]

def analyze_posts_batch(texts: list[str]):
    error_result = {
        "content_category": "分析失敗", "expression_category": "分析失敗",
        "style_stance_category": "分析失敗", "embedding": None
    }
    if not API_KEY:
        print("エラー: GEMINI_API_KEYが設定されていません。")
        return [error_result] * len(texts)

    try:
        # all-mpnet-base-v2 の次元数は 768 です。
        embeddings = embedding_model.encode(texts).tolist()
    except Exception as e:
        print(f"テキストのベクトル化中にエラーが発生しました: {e}")
        embeddings = [None] * len(texts)

    if not texts:
        return []

    formatted_texts = "\n".join(f"投稿{i+1}:\n---\n{text}\n---" for i, text in enumerate(texts))

    # ▼▼▼【変更】Few-shotプロンプティングを新しいカテゴリ定義に更新 ▼▼▼
    prompt = f"""
    以下のSNS投稿リスト（{len(texts)}件）を分析し、3つの軸で最も適切なカテゴリを1つずつ選択してください。
    回答は、JSONオブジェクトのリスト形式で、投稿の順番通りに出力してください。

    # 分析の軸:
    1. content_category: 投稿の主要な内容 (Yahoo!知恵袋ベース)
    2. expression_category: 投稿全体の感情的な表現 (27感情ベース)
    3. style_stance_category: 投稿の文体やスタンス (クソリプ分類ベース)

    # カテゴリリスト (必ずこの中から選択):
    - "content_category": {flat_content_categories}
    - "expression_category": {EXPRESSION_CATEGORIES}
    - "style_stance_category": {STYLE_STANCE_CATEGORIES}

    # 分類例 (このような形式で分類してください):
    - 投稿例: 「新しいプロジェクトが無事完了！チームのみんな、本当にお疲れ様でした！最高のメンバーに感謝！」
      - "content_category": "仕事・キャリア"
      - "expression_category": "喜び"
      - "style_stance_category": "感謝・ポジティブな反応"
    - 投稿例: 「今日のランチはパスタ。まあまあ美味しかった。」
      - "content_category": "料理、レシピ"
      - "expression_category": "満足"
      - "style_stance_category": "一般的な意見・感想"
    - 投稿例: 「なんでいつもこうなるの？本当にありえない。もう我慢の限界。」
      - "content_category": "人間関係の悩み"
      - "expression_category": "嫌悪"
      - "style_stance_category": "全否定"
    - 投稿例: 「お前バカだなｗそんなことも知らんのか」
      - "content_category": "雑談"
      - "expression_category": "嫌悪"
      - "style_stance_category": "侮辱"

    # 制約（絶対に守ってください）:
    - 必ず投稿{len(texts)}件分、つまり{len(texts)}個のJSONオブジェクトをリストに入れて返してください。
    - 分析が困難な場合でも、カテゴリを「その他」や「その他・分類不能」として必ずオブジェクトを作成してください。
    - 回答はJSONリストのみとし、説明文は一切含めないでください。
    - 各JSONオブジェクトには3つのキー（content_category, expression_category, style_stance_category）を必ず含めてください。
    - **最終出力の前に、生成したJSONオブジェクトの数が{len(texts)}個であることを必ず確認してください。数が違う場合は、リストを修正して{len(texts)}個にしてください。**

    # 投稿リスト:
    {formatted_texts}

    # 出力形式 (JSONリスト):
    [
      {{"content_category": "...", "expression_category": "...", "style_stance_category": "..."}},
      ...
    ]
    """
    try:
        response = model.generate_content(prompt)
        match = re.search(r'```json\s*(\[.*\])\s*```|(\[.*\])', response.text, re.DOTALL)
        if not match:
            print("エラー: LLM応答からJSONリストが見つかりません。")
            print(f"--- LLMからの応答 ---\n{response.text}\n--------------------")
            return [error_result] * len(texts)

        json_text = match.group(1) or match.group(2)
        analysis_results_json = json.loads(json_text)

        if isinstance(analysis_results_json, list) and len(analysis_results_json) == len(texts):
            full_results = []
            for i, result in enumerate(analysis_results_json):
                final_result = {
                    "content_category": result.get("content_category", "その他"),
                    "expression_category": result.get("expression_category", "その他・分類不能"),
                    "style_stance_category": result.get("style_stance_category", "その他"),
                    "embedding": embeddings[i]
                }
                full_results.append(final_result)
            return full_results
        else:
            print(f"エラー: LLMからの結果件数が一致しません。(期待: {len(texts)}, 実際: {len(analysis_results_json)})")
            print(f"--- LLMからの応答 ---\n{response.text}\n--------------------")
            return [error_result] * len(texts)

    except json.JSONDecodeError as e:
        print(f"JSONの解析に失敗しました: {e}")
        print(f"--- LLMからの応答 ---\n{response.text}\n--------------------")
        return [error_result] * len(texts)
    except Exception as e:
        print(f"LLMでの分析中に予期せぬエラーが発生しました: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"--- LLMからの応答 ---\n{response.text}\n--------------------")
        return [error_result] * len(texts)