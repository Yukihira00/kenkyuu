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

# --- あなたのカテゴリ案に基づき、50個の選択肢を定義 ---

# 「内容・トピック」による分類 (50項目)
TOPIC_CATEGORIES = [
    "食事・グルメ", "健康・ウェルネス", "美容・ファッション", "育児・家族", "ペット", "住まい・インテリア",
    "個人の出来事", "ゲーム", "漫画・アニメ", "映画・ドラマ", "音楽", "読書", "スポーツ観戦", "アート・創作",
    "アイドル・有名人", "国内旅行", "海外旅行", "地域情報・イベント", "乗り物", "キャリア・就職", "スキルアップ",
    "学問・研究", "業界ニュース", "ニュース速報", "政治", "経済", "社会問題", "国際情勢", "ガジェット・デバイス",
    "ソフトウェア・アプリ", "Webサービス", "AI・機械学習", "プログラミング", "商品レビュー", "おすすめ・推薦",
    "セール・お得情報", "新商品情報", "事実の報告", "知識・ノウハウの共有", "イベントの告知", "個人的な見解",
    "問題提起", "悩み相談", "単純な疑問", "専門的な質問", "個人的な日記", "進捗報告", "思考の整理", "挨拶", "その他"
]

# 「感情・トーン・意図」による分類 (50項目)
TONE_CATEGORIES = [
    "喜び・幸福", "興奮・期待", "感謝・賞賛", "感動・心温まる", "安らぎ・癒やし", "満足・達成感", "愛情・友情",
    "楽観的", "怒り・不満", "悲しみ・失望", "不安・恐怖", "批判・非難", "嫉妬・羨望", "後悔・反省", "疲労・倦怠感",
    "無気力・退屈", "客観的・事実ベース", "淡々とした報告", "中立的な意見", "データの提示", "ユーモラス",
    "皮肉・風刺", "自虐的", "面白い・滑稽", "冗談・ネタ", "真面目・専門的", "啓発的・教育的", "深刻・重大",
    "公式発表", "丁寧・謙虚", "断定的・強い主張", "問いかけ・疑問提起", "意見の募集", "情報共有の意図",
    "議論の喚起", "共感の希求", "娯楽の提供", "宣伝・販売促進", "自己PR", "記録・備忘録", "コミュニケーション",
    "他者への返信", "応援・激励", "警告・注意喚起", "謝罪", "挑発的", "曖昧・婉曲的", "その他"
]
# -----------------------------------------------------------------

def analyze_post_text(text: str):
    """
    投稿テキストをGemini APIに送信し、トピックとトーンを分析して返す。
    """
    if not API_KEY:
        print("エラー: GEMINI_API_KEYが設定されていません。")
        return None

    # LLMへの指示（プロンプト）を作成
    prompt = f"""
    以下のSNS投稿を分析し、最も適切な「トピック」と「トーン」をそれぞれ1つだけ選択して、JSON形式で回答してください。

    # 制約:
    - 「トピック」は必ず以下のリストから選択してください: {TOPIC_CATEGORIES}
    - 「トーン」は必ず以下のリストから選択してください: {TONE_CATEGORIES}
    - 回答はJSONオブジェクトのみとし、前後に説明文などを付けないでください。

    # 投稿テキスト:
    "{text}"

    # 出力形式:
    {{
      "topic": "（選択したトピック）",
      "tone": "（選択したトーン）"
    }}
    """

    try:
        # LLMにリクエストを送信
        response = model.generate_content(prompt)
        
        # レスポンスからJSON部分を抽出
        json_text = response.text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:-3].strip()
        
        # JSON文字列をPythonの辞書に変換
        analysis_result = json.loads(json_text)
        
        # 想定したキーが存在するかチェック
        if "topic" in analysis_result and "tone" in analysis_result:
            return analysis_result
        else:
            print(f"エラー: LLMからのレスポンス形式が不正です。Response: {response.text}")
            return None

    except Exception as e:
        print(f"LLMでの分析中にエラーが発生しました: {e}")
        return None

# --- このファイル単体でテストするためのコード ---
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