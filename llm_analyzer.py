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
# ▼▼▼【変更】モデルを高性能なものに変更 ▼▼▼
model = genai.GenerativeModel('gemini-2.5-flash')
# ▼▼▼【変更】埋め込みモデルを高性能なものに変更 ▼▼▼
embedding_model = SentenceTransformer('all-mpnet-base-v2')

# --- カテゴリ定義 ---
CONTENT_CATEGORIES = {
    "暮らし": ["食事・料理", "住まい・暮らし", "お出かけ・旅行", "健康・ウェルネス", "美容・ファッション", "買い物・消費", "家族・育児", "ペット"],
    "趣味": ["カルチャー（映画・音楽等）", "ゲーム", "スポーツ", "創作・表現", "アウトドア", "学び・探求"],
    "仕事と社会": ["仕事・キャリア", "学習・スキル", "テクノロジー", "経済・金融", "社会・時事", "人間関係"]
}

EXPRESSION_CATEGORIES = [
    "肯定的", "中立・客観的", "懸念・不安", "悲しみ・失望",
    "怒り・不満", "攻撃的", "ショッキング"
]

STYLE_STANCE_CATEGORIES = [
    "自慢・成功誇示", "感謝・ポジティブな感想", "ユーモア・ジョーク",
    "批判・反論", "愚痴・不平不満", "皮肉・冷笑", "過度な自虐",
    "強い意見・主張", "教訓・アドバイス", "客観的な報告・告知",
    "専門的な解説", "不正確・誤情報", "根拠のない陰謀論",
    "扇情的な見出し（釣りタイトル）", "誇張・大げさな表現", "丁寧・謙虚",
    "当たり障りのない意見", "内省的・思索的", "感情的な共感を求める",
    "その他"
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
        # ▼▼▼【変更】埋め込みの次元数に合わせてデータベースのカラムサイズも変更が必要です ▼▼▼
        # all-mpnet-base-v2 の次元数は 768 です。
        # database.py の post_analysis_cache テーブルの embedding カラムを vector(768) に変更してください。
        embeddings = embedding_model.encode(texts).tolist()
    except Exception as e:
        print(f"テキストのベクトル化中にエラーが発生しました: {e}")
        embeddings = [None] * len(texts)

    if not texts:
        return []

    formatted_texts = "\n".join(f"投稿{i+1}:\n---\n{text}\n---" for i, text in enumerate(texts))

    # ▼▼▼【変更】Few-shotプロンプティングを追加し、AIへの指示をより具体的に ▼▼▼
    prompt = f"""
    以下のSNS投稿リスト（{len(texts)}件）を分析し、3つの軸で最も適切なカテゴリを1つずつ選択してください。
    回答は、JSONオブジェクトのリスト形式で、投稿の順番通りに出力してください。

    # 分析の軸:
    1. content_category: 投稿の主要な内容
    2. expression_category: 投稿全体の感情的な表現
    3. style_stance_category: 投稿の文体やスタンス

    # カテゴリリスト (必ずこの中から選択):
    - "content_category": {flat_content_categories}
    - "expression_category": {EXPRESSION_CATEGORIES}
    - "style_stance_category": {STYLE_STANCE_CATEGORIES}

    # 分類例 (このような形式で分類してください):
    - 投稿例: 「新しいプロジェクトが無事完了！チームのみんな、本当にお疲れ様でした！最高のメンバーに感謝！」
      - "content_category": "仕事・キャリア"
      - "expression_category": "肯定的"
      - "style_stance_category": "感謝・ポジティブな感想"
    - 投稿例: 「今日のランチはパスタ。まあまあ美味しかった。」
      - "content_category": "食事・料理"
      - "expression_category": "中立・客観的"
      - "style_stance_category": "当たり障りのない意見"
    - 投稿例: 「なんでいつもこうなるの？本当にありえない。もう我慢の限界。」
      - "content_category": "人間関係"
      - "expression_category": "怒り・不満"
      - "style_stance_category": "愚痴・不平不満"

    # 制約（絶対に守ってください）:
    - 必ず投稿{len(texts)}件分、つまり{len(texts)}個のJSONオブジェクトをリストに入れて返してください。
    - 分析が困難な場合でも、カテゴリを「不明」として必ずオブジェクトを作成してください。
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
                    "content_category": result.get("content_category", "不明"),
                    "expression_category": result.get("expression_category", "不明"),
                    "style_stance_category": result.get("style_stance_category", "不明"),
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