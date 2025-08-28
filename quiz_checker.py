# 全60問の質問リスト
questions = [
    # 1-10
    "芸術の重要性を信じている。",
    "物事を整理整頓するのが好きだ。",
    "怒るべき相手にも優しく接する。",
    "普段あまり人と話さない。",
    "自分は臆病者だと思う。",
    "相手から何かを得たいときは、相手の冗談がつまらなくても笑って合わせてしまう。",
    "歴史や科学を学ぶことに興味がある。",
    "目標を達成するためには自分を追い込む。",
    "毒舌になることがある。",
    "即興で人前で話すのが得意だ。",
    # 11-20
    "普段いろいろなことを心配する。",
    "絶対にバレないってわかってたら、 1 億円くらい盗んじゃうかも。",
    "直感的なひらめきが急に訪れることはほとんどない。",
    "すべてが完璧になるまでやり続ける。",
    "自分の要求が多く、満足しにくい。",
    "友達を作るのが得意だ。",
    "他人に影響されやすい。",
    "大金持ちになることは、私にとってそれほど重要ではない。",
    "人から変わり者だと思われている。",
    "よく考えずに決めてしまうことがある。",
    # 21-30
    "めったに他の人に対して怒りを感じない。",
    "たいてい元気いっぱいで活発に動いている。",
    "悲しい出来事を聞くとすぐに悲しくなる。",
    "自分は特別ではなくただの普通の人間だと思う。",
    "新しいアイデアを考えるのが大好きだ。",
    "仕事で最高の品質を追求したい。",
    "他人を許すのが難しい。",
    "飲み会では盛り上げ役になる。",
    "危険が迫るとパニックになるだろう。",
    "出世のために上司にゴマすりするのは、うまくいきそうでも避けている。",
    # 31-40
    "世間の常識とは違うことをする人が好きだ。",
    "事前に計画を立てて、その通りに行動するようにしている。",
    "相手が期待に応えてくれないとき、イライラして怒ることがある。",
    "リーダーシップを発揮できる。",
    "結局は大したことのないことでよく心配する。",
    "いくら大金でも、賄賂は受け取るつもりはない。",
    "絵画や写真の感情的な側面にほとんど気づかない。",
    "物を元の場所に戻すのをよく忘れる。",
    "他人のミスにイライラする。",
    "社交的なやり取りが多い仕事は苦手だろう。",
    # 41-50
    "誰かに守られたいと感じる。",
    "高いブランド品とか持ってると、すごく幸せな気分になる。",
    "何かを深く調べて探求することはないだろう。",
    "仕事に厳密さを求める。",
    "ちょっとしたことでイライラしやすい。",
    "よく声を出して笑う。",
    "他の人の感情を自分のことのように感じる。",
    "自分は普通の人よりも注目される存在だと思う。",
    "想像力があまり豊かではない。",
    "細部にこだわる。",
    # 51-60
    "めったに文句や不満を言わない。",
    "勢いよく、賑やかに笑う。",
    "危険な状況に直面すると震えが止まらない。",
    "何かを頼むために、その人のことが好きなフリはしたくない。",
    "哲学など抽象的なことには興味がない。",
    "計画に従って物事を進める。",
    "自分が整理したものを他人が変えるとイライラする。",
    "他人に話しかけるのが難しいと感じることがある。",
    "他人の必要としていることに対して敏感に反応する。",
    "捕まる心配がないなら、偽札使ってみたい気がする。"
]

# 新しい質問リストに対応した採点キー
HEXACO_MAPPING = {
    # H: Honesty-Humility (正直さ-謙虚さ)
    6: {'trait': 'H', 'reversed': True},   # 相手に合わせる (不誠実)
    12: {'trait': 'H', 'reversed': True},  # 盗むかも (不正)
    18: {'trait': 'H', 'reversed': False}, # 金持ちは重要でない (貪欲でない)
    24: {'trait': 'H', 'reversed': False}, # 自分は普通 (謙虚)
    30: {'trait': 'H', 'reversed': False}, # ゴマすりを避ける (誠実)
    36: {'trait': 'H', 'reversed': False}, # 賄賂を受け取らない (公正)
    42: {'trait': 'H', 'reversed': True},  # ブランド品で幸せ (物質主義)
    48: {'trait': 'H', 'reversed': True},  # 注目される存在だと思う (うぬぼれ)
    54: {'trait': 'H', 'reversed': False}, # 好きなフリはしない (誠実)
    60: {'trait': 'H', 'reversed': True},  # 偽札を使ってみたい (不正)

    # E: Emotionality (情緒性)
    5: {'trait': 'E', 'reversed': False},  # 臆病者だと思う (恐怖)
    11: {'trait': 'E', 'reversed': False}, # いろいろ心配する (不安)
    17: {'trait': 'E', 'reversed': False}, # 他人に影響されやすい (依存)
    23: {'trait': 'E', 'reversed': False}, # すぐに悲しくなる (感傷)
    29: {'trait': 'E', 'reversed': False}, # パニックになる (恐怖)
    35: {'trait': 'E', 'reversed': False}, # 大したことないことで心配 (不安)
    41: {'trait': 'E', 'reversed': False}, # 誰かに守られたい (依存)
    47: {'trait': 'E', 'reversed': False}, # 他人の感情を自分のことのように (共感)
    53: {'trait': 'E', 'reversed': False}, # 震えが止まらない (恐怖)
    59: {'trait': 'E', 'reversed': False}, # 他人の必要に敏感 (共感)

    # X: Extraversion (外向性)
    4: {'trait': 'X', 'reversed': True},   # あまり人と話さない (内気)
    10: {'trait': 'X', 'reversed': False}, # 人前で話すのが得意 (社会的自信)
    16: {'trait': 'X', 'reversed': False}, # 友達を作るのが得意 (社交性)
    22: {'trait': 'X', 'reversed': False}, # 元気いっぱいで活発 (活気)
    28: {'trait': 'X', 'reversed': False}, # 盛り上げ役になる (社交性)
    34: {'trait': 'X', 'reversed': False}, # リーダーシップを発揮 (社会的自信)
    40: {'trait': 'X', 'reversed': True},  # 社交的な仕事は苦手 (内気)
    46: {'trait': 'X', 'reversed': False}, # よく声を出して笑う (陽気)
    52: {'trait': 'X', 'reversed': False}, # 勢いよく賑やかに笑う (陽気)
    58: {'trait': 'X', 'reversed': True},  # 話しかけるのが難しい (内気)

    # A: Agreeableness (協調性)
    3: {'trait': 'A', 'reversed': False},  # 優しく接する (寛容)
    9: {'trait': 'A', 'reversed': True},   # 毒舌になることがある (短気)
    15: {'trait': 'A', 'reversed': True},  # 要求が多く満足しにくい (批判的)
    21: {'trait': 'A', 'reversed': False}, # めったに怒らない (我慢強い)
    27: {'trait': 'A', 'reversed': True},  # 他人を許すのが難しい (執念深い)
    33: {'trait': 'A', 'reversed': True},  # イライラして怒る (短気)
    39: {'trait': 'A', 'reversed': True},  # 他人のミスにイライラ (短気)
    45: {'trait': 'A', 'reversed': True},  # イライラしやすい (短気)
    51: {'trait': 'A', 'reversed': False}, # めったに文句を言わない (我慢強い)
    57: {'trait': 'A', 'reversed': True},  # 他人が変えるとイライラ (短気)

    # C: Conscientiousness (誠実性)
    2: {'trait': 'C', 'reversed': False},  # 整理整頓が好き (秩序)
    8: {'trait': 'C', 'reversed': False},  # 自分を追い込む (勤勉)
    14: {'trait': 'C', 'reversed': False}, # 完璧になるまでやる (完璧主義)
    20: {'trait': 'C', 'reversed': True},  # よく考えずに決める (衝動的)
    26: {'trait': 'C', 'reversed': False}, # 最高の品質を追求 (完璧主義)
    32: {'trait': 'C', 'reversed': False}, # 計画通りに行動 (計画性)
    38: {'trait': 'C', 'reversed': True},  # 元の場所に戻すのを忘れる (無秩序)
    44: {'trait': 'C', 'reversed': False}, # 仕事に厳密さを求める (勤勉)
    50: {'trait': 'C', 'reversed': False}, # 細部にこだわる (完璧主義)
    56: {'trait': 'C', 'reversed': False}, # 計画に従って進める (計画性)

    # O: Openness to Experience (開放性)
    1: {'trait': 'O', 'reversed': False},  # 芸術の重要性を信じる (審美眼)
    7: {'trait': 'O', 'reversed': False},  # 歴史や科学に興味 (好奇心)
    13: {'trait': 'O', 'reversed': True},  # ひらめきはほとんどない (非創造的)
    19: {'trait': 'O', 'reversed': False}, # 変わり者だと思われている (非慣習的)
    25: {'trait': 'O', 'reversed': False}, # 新しいアイデアが好き (創造性)
    31: {'trait': 'O', 'reversed': False}, # 常識と違う人が好き (非慣習的)
    37: {'trait': 'O', 'reversed': True},  # 感情的な側面に気づかない (審美眼が低い)
    43: {'trait': 'O', 'reversed': True},  # 探求することはない (好奇心が低い)
    49: {'trait': 'O', 'reversed': True},  # 想像力が豊かではない (非創造的)
    55: {'trait': 'O', 'reversed': True},  # 哲学などに興味がない (好奇心が低い)
}

def run_quiz():
    """コンソールでHEXACO診断を実行し、回答をリストとして返す"""
    print("これから性格診断を始めます。")
    print("各質問に対し、1（まったく当てはまらない）から5（すごく当てはまる）の数字で回答してください。")
    print("-" * 30)
    
    answers = []
    for i, question_text in enumerate(questions, 1):
        while True:
            answer_str = input(f"質問{i}: {question_text}\nあなたの回答 (1-5): ")
            if answer_str in ["1", "2", "3", "4", "5"]:
                answers.append(int(answer_str))
                break
            else:
                print("エラー: 1から5の半角数字で入力してください。")
    
    return answers

def calculate_scores(answers):
    """60個の回答リストを受け取り、HEXACOの6つのスコアを計算して返す"""
    
    # 各性格特性のスコアを初期化
    scores = {'H': 0, 'E': 0, 'X': 0, 'A': 0, 'C': 0, 'O': 0}
    # 各性格特性の質問数をカウント
    counts = {'H': 0, 'E': 0, 'X': 0, 'A': 0, 'C': 0, 'O': 0}

    # 回答を一つずつループ処理
    for i, answer in enumerate(answers, 1):
        if i in HEXACO_MAPPING:
            info = HEXACO_MAPPING[i]
            trait = info['trait']
            
            # 逆転項目の場合はスコアを反転させる (5→1, 4→2, 3→3, 2→4, 1→5)
            score = (6 - answer) if info['reversed'] else answer
            
            scores[trait] += score
            counts[trait] += 1
    
    # 各特性の合計点数を質問数で割り、平均点を計算
    averages = {trait: scores[trait] / counts[trait] for trait in scores}
    
    return averages

if __name__ == "__main__":
    # テストの際は、下の行のコメントを外すと、全問「3」で回答したとして即座に結果を確認できます
    # user_answers = [3] * 60 
    
    # 実際にクイズを実行する場合は、下の行のコメントを有効にしてください
    user_answers = run_quiz()
    
    print("-" * 30)
    print("診断お疲れ様でした！")
    print(f"あなたの回答リスト: {user_answers}")

    # 最終スコアを計算して表示
    final_scores = calculate_scores(user_answers)
    print("\n計算された性格スコア (各特性の平均点):")
    for trait, score in final_scores.items():
        # .2f は小数点以下2桁まで表示するという意味
        print(f"  {trait}: {score:.2f}")