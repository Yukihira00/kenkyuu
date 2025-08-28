# 質問、特性、逆転項目の情報をすべてまとめたリスト
QUESTIONS_DATA = [
    {'id': 1, 'text': '芸術の重要性を信じている。', 'trait': 'O', 'reversed': False},
    {'id': 2, 'text': '物事を整理整頓するのが好きだ。', 'trait': 'C', 'reversed': False},
    {'id': 3, 'text': '怒るべき相手にも優しく接する。', 'trait': 'A', 'reversed': False},
    {'id': 4, 'text': '普段あまり人と話さない。', 'trait': 'X', 'reversed': True},
    {'id': 5, 'text': '自分は臆病者だと思う。', 'trait': 'E', 'reversed': False},
    {'id': 6, 'text': '相手から何かを得たいときは、相手の冗談がつまらなくても笑って合わせてしまう。', 'trait': 'H', 'reversed': True},
    {'id': 7, 'text': '歴史や科学を学ぶことに興味がある。', 'trait': 'O', 'reversed': False},
    {'id': 8, 'text': '目標を達成するためには自分を追い込む。', 'trait': 'C', 'reversed': False},
    {'id': 9, 'text': '毒舌になることがある。', 'trait': 'A', 'reversed': True},
    {'id': 10, 'text': '即興で人前で話すのが得意だ。', 'trait': 'X', 'reversed': False},
    {'id': 11, 'text': '普段いろいろなことを心配する。', 'trait': 'E', 'reversed': False},
    {'id': 12, 'text': '絶対にバレないってわかってたら、 1 億円くらい盗んじゃうかも。', 'trait': 'H', 'reversed': True},
    {'id': 13, 'text': '直感的なひらめきが急に訪れることはほとんどない。', 'trait': 'O', 'reversed': True},
    {'id': 14, 'text': 'すべてが完璧になるまでやり続ける。', 'trait': 'C', 'reversed': False},
    {'id': 15, 'text': '自分の要求が多く、満足しにくい。', 'trait': 'A', 'reversed': True},
    {'id': 16, 'text': '友達を作るのが得意だ。', 'trait': 'X', 'reversed': False},
    {'id': 17, 'text': '他人に影響されやすい。', 'trait': 'E', 'reversed': False},
    {'id': 18, 'text': '大金持ちになることは、私にとってそれほど重要ではない。', 'trait': 'H', 'reversed': False},
    {'id': 19, 'text': '人から変わり者だと思われている。', 'trait': 'O', 'reversed': False},
    {'id': 20, 'text': 'よく考えずに決めてしまうことがある。', 'trait': 'C', 'reversed': True},
    {'id': 21, 'text': 'めったに他の人に対して怒りを感じない。', 'trait': 'A', 'reversed': False},
    {'id': 22, 'text': 'たいてい元気いっぱいで活発に動いている。', 'trait': 'X', 'reversed': False},
    {'id': 23, 'text': '悲しい出来事を聞くとすぐに悲しくなる。', 'trait': 'E', 'reversed': False},
    {'id': 24, 'text': '自分は特別ではなくただの普通の人間だと思う。', 'trait': 'H', 'reversed': False},
    {'id': 25, 'text': '新しいアイデアを考えるのが大好きだ。', 'trait': 'O', 'reversed': False},
    {'id': 26, 'text': '仕事で最高の品質を追求したい。', 'trait': 'C', 'reversed': False},
    {'id': 27, 'text': '他人を許すのが難しい。', 'trait': 'A', 'reversed': True},
    {'id': 28, 'text': '飲み会では盛り上げ役になる。', 'trait': 'X', 'reversed': False},
    {'id': 29, 'text': '危険が迫るとパニックになるだろう。', 'trait': 'E', 'reversed': False},
    {'id': 30, 'text': '出世のために上司にゴマすりするのは、うまくいきそうでも避けている。', 'trait': 'H', 'reversed': False},
    {'id': 31, 'text': '世間の常識とは違うことをする人が好きだ。', 'trait': 'O', 'reversed': False},
    {'id': 32, 'text': '事前に計画を立てて、その通りに行動するようにしている。', 'trait': 'C', 'reversed': False},
    {'id': 33, 'text': '相手が期待に応えてくれないとき、イライラして怒ることがある。', 'trait': 'A', 'reversed': True},
    {'id': 34, 'text': 'リーダーシップを発揮できる。', 'trait': 'X', 'reversed': False},
    {'id': 35, 'text': '結局は大したことのないことでよく心配する。', 'trait': 'E', 'reversed': False},
    {'id': 36, 'text': 'いくら大金でも、賄賂は受け取るつもりはない。', 'trait': 'H', 'reversed': False},
    {'id': 37, 'text': '絵画や写真の感情的な側面にほとんど気づかない。', 'trait': 'O', 'reversed': True},
    {'id': 38, 'text': '物を元の場所に戻すのをよく忘れる。', 'trait': 'C', 'reversed': True},
    {'id': 39, 'text': '他人のミスにイライラする。', 'trait': 'A', 'reversed': True},
    {'id': 40, 'text': '社交的なやり取りが多い仕事は苦手だろう。', 'trait': 'X', 'reversed': True},
    {'id': 41, 'text': '誰かに守られたいと感じる。', 'trait': 'E', 'reversed': False},
    {'id': 42, 'text': '高いブランド品とか持ってると、すごく幸せな気分になる。', 'trait': 'H', 'reversed': True},
    {'id': 43, 'text': '何かを深く調べて探求することはないだろう。', 'trait': 'O', 'reversed': True},
    {'id': 44, 'text': '仕事に厳密さを求める。', 'trait': 'C', 'reversed': False},
    {'id': 45, 'text': 'ちょっとしたことでイライラしやすい。', 'trait': 'A', 'reversed': True},
    {'id': 46, 'text': 'よく声を出して笑う。', 'trait': 'X', 'reversed': False},
    {'id': 47, 'text': '他の人の感情を自分のことのように感じる。', 'trait': 'E', 'reversed': False},
    {'id': 48, 'text': '自分は普通の人よりも注目される存在だと思う。', 'trait': 'H', 'reversed': True},
    {'id': 49, 'text': '想像力があまり豊かではない。', 'trait': 'O', 'reversed': True},
    {'id': 50, 'text': '細部にこだわる。', 'trait': 'C', 'reversed': False},
    {'id': 51, 'text': 'めったに文句や不満を言わない。', 'trait': 'A', 'reversed': False},
    {'id': 52, 'text': '勢いよく、賑やかに笑う。', 'trait': 'X', 'reversed': False},
    {'id': 53, 'text': '危険な状況に直面すると震えが止まらない。', 'trait': 'E', 'reversed': False},
    {'id': 54, 'text': '何かを頼むために、その人のことが好きなフリはしたくない。', 'trait': 'H', 'reversed': False},
    {'id': 55, 'text': '哲学など抽象的なことには興味がない。', 'trait': 'O', 'reversed': True},
    {'id': 56, 'text': '計画に従って物事を進める。', 'trait': 'C', 'reversed': False},
    {'id': 57, 'text': '自分が整理したものを他人が変えるとイライラする。', 'trait': 'A', 'reversed': True},
    {'id': 58, 'text': '他人に話しかけるのが難しいと感じることがある。', 'trait': 'X', 'reversed': True},
    {'id': 59, 'text': '他人の必要としていることに対して敏感に反応する。', 'trait': 'E', 'reversed': False},
    {'id': 60, 'text': '捕まる心配がないなら、偽札使ってみたい気がする。', 'trait': 'H', 'reversed': True},
]

def calculate_scores(answers: list[int]):
    """60個の回答リストを受け取り、HEXACOの6つのスコアを計算して返す"""
    scores = {'H': 0, 'E': 0, 'X': 0, 'A': 0, 'C': 0, 'O': 0}
    counts = {'H': 0, 'E': 0, 'X': 0, 'A': 0, 'C': 0, 'O': 0}

    for i, answer in enumerate(answers):
        # 質問データは0から始まるリストなので、インデックスiで直接アクセス
        info = QUESTIONS_DATA[i]
        trait = info['trait']
        
        score = (6 - answer) if info['reversed'] else answer
        
        scores[trait] += score
        counts[trait] += 1
    
    # 割り算がゼロ除算にならないようにチェック
    averages = {trait: scores[trait] / counts[trait] if counts[trait] > 0 else 0 for trait in scores}
    return averages