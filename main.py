import secrets
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# 自作モジュールのインポート
import database
import quiz_checker
import timeline_checker
import personality_descriptions

# --- アプリケーションの初期設定 ---
app = FastAPI()

# セッション機能の追加 (ユーザーのログイン状態を記憶するため)
# secret_keyはアプリを起動するたびに変わるランダムな文字列になります
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))

# HTMLテンプレートを読み込む設定
templates = Jinja2Templates(directory="templates")


# --- ルート設定 ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    トップページ。ログインしていればタイムラインへ、していなければログインページへリダイレクトする。
    """
    if 'user_did' in request.session:
        return RedirectResponse(url="/timeline", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    """
    ログインフォームを表示する。
    """
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_process(request: Request, handle: str = Form(...), app_password: str = Form(...)):
    """
    フォームから送信された情報でログイン処理を行う。
    """
    # timeline_checker を使ってログインを試みる
    user_profile = timeline_checker.verify_login_and_get_profile(handle, app_password)

    if user_profile:
        # ログイン成功
        # セッションにユーザー情報を保存
        request.session['user_did'] = user_profile['did']
        request.session['user_handle'] = user_profile['handle']
        request.session['user_display_name'] = user_profile['display_name']
        request.session['app_password'] = app_password  # ★★★ この行を追加 ★★★

        # データベースに診断結果があるか確認
        result = database.get_user_result(user_profile['did'])
        if result:
            # 診断済みならタイムラインへ
            return RedirectResponse(url="/timeline", status_code=303)
        else:
            # 未診断なら診断ページへ
            return RedirectResponse(url="/quiz", status_code=303)
    else:
        # ログイン失敗
        # エラーメッセージ付きでログインページを再表示
        return templates.TemplateResponse("login.html", {"request": request, "error": "ハンドルまたはアプリパスワードが間違っています。"})


@app.get("/quiz", response_class=HTMLResponse)
async def quiz_form(request: Request):
    """
    性格診断の質問ページを表示する。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    questions = quiz_checker.QUESTIONS_DATA # 質問リストを取得
    return templates.TemplateResponse("quiz.html", {"request": request, "questions": questions})


@app.post("/submit")
async def submit_quiz(request: Request):
    """
    性格診断の回答を処理し、データベースに保存した後、結果ページへリダイレクトする。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)

    form_data = await request.form()
    
    answers = []
    for i in range(1, len(quiz_checker.QUESTIONS_DATA) + 1):
        answer = form_data.get(f'q{i}')
        if answer:
            answers.append(int(answer))
    
    if len(answers) == len(quiz_checker.QUESTIONS_DATA):
        scores = quiz_checker.calculate_scores(answers)
        
        user_did = request.session['user_did']
        user_handle = request.session['user_handle']
        database.add_or_update_hexaco_result(user_did, user_handle, scores)
        
        # タイムラインではなく、結果ページへリダイレクト
        return RedirectResponse(url="/results", status_code=303)
    else:
        # (変更なし)
        questions = quiz_checker.QUESTIONS_DATA
        return templates.TemplateResponse(
            "quiz.html", 
            {
                "request": request, 
                "questions": questions,
                "error": "すべての質問に回答してください。"
            }
        )


@app.get("/timeline", response_class=HTMLResponse)
async def show_timeline(request: Request):
    """
    パーソナライズされたタイムラインを表示する（準備段階）。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
        
    user_info = {
        "did": request.session['user_did'],
        "handle": request.session['user_handle'],
        "display_name": request.session['user_display_name']
    }

    # ここに将来的にタイムライン取得とフィルタリングのロジックが入る
    # timeline = timeline_checker.get_timeline_data(...)
    # filtered_timeline = filter_logic(timeline, scores)

    return templates.TemplateResponse("timeline.html", {"request": request, "user": user_info})


@app.get("/logout")
async def logout(request: Request):
    """
    ログアウト処理。セッションをクリアしてログインページに戻す。
    """
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/results", response_class=HTMLResponse)
async def show_results(request: Request):
    """
    データベースから最新の診断結果を取得し、解説付きで表示する。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
        
    user_did = request.session['user_did']
    result = database.get_user_result(user_did)
    
    if not result:
        # 結果がない場合 (通常は起こらないが念のため)
        return RedirectResponse(url="/quiz", status_code=302)

    # データベースから取得したスコアを整形
    scores = {
        'H': result['h'], 'E': result['e'], 'X': result['x'],
        'A': result['a'], 'C': result['c'], 'O': result['o']
    }

    return templates.TemplateResponse(
        "results.html", 
        {
            "request": request,
            "scores": scores,
            "descriptions": personality_descriptions.DESCRIPTIONS
        }
    )