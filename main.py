from datetime import datetime
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
import llm_analyzer

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
    パーソナライズされたタイムラインを表示する。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    # ▼▼▼ .get() を使って、より安全にセッションからデータを取得する ▼▼▼
    # 表示名があればそれを使い、なければハンドルを'display_name'として使う
    display_name = request.session.get('user_display_name') or request.session.get('user_handle')

    user_info = {
        "did": request.session.get('user_did'),
        "handle": request.session.get('user_handle'),
        "display_name": display_name
    }
    # ▲▲▲ ここまで ▲▲▲

    handle = request.session.get('user_handle')
    app_password = request.session.get('app_password')

    feed_data = None
    if handle and app_password:
        feed_data = timeline_checker.get_timeline_data(handle, app_password, limit=100)

    if feed_data:
        for item in feed_data:
            if isinstance(item.post.indexed_at, str):
                dt_str = item.post.indexed_at.replace('Z', '+00:00')
                item.post.indexed_at = datetime.fromisoformat(dt_str)

    return templates.TemplateResponse("timeline.html", {
        "request": request,
        "user": user_info,
        "feed": feed_data
    })

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

@app.get("/settings", response_class=HTMLResponse)
async def show_settings(request: Request):
    """
    フィルター設定ページを表示する
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    user_did = request.session['user_did']
    
    # ユーザーの現在の設定を取得
    user_settings = database.get_user_filter_settings(user_did)
    
    # ★★★ llm_analyzerから階層化されたカテゴリリストを取得 ★★★
    all_content_categories = llm_analyzer.CONTENT_CATEGORIES
    all_expression_categories = llm_analyzer.EXPRESSION_CATEGORIES
    all_style_stance_categories = llm_analyzer.STYLE_STANCE_CATEGORIES
    
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user_settings": user_settings,
            "all_content_categories": all_content_categories,
            "all_expression_categories": all_expression_categories,
            "all_style_stance_categories": all_style_stance_categories,
        }
    )

@app.post("/settings")
async def save_settings(request: Request):
    """
    フィルター設定を保存する
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    user_did = request.session['user_did']
    form_data = await request.form()
    
    # フォームからチェックされたリストを取得
    hidden_content = form_data.getlist("hidden_content")
    hidden_expression = form_data.getlist("hidden_expression")
    hidden_style_stance = form_data.getlist("hidden_style_stance")
    
    # データベースに保存
    database.save_user_filter_settings(user_did, hidden_content, hidden_expression, hidden_style_stance)
    
    # --- ここが重要です ---
    # ページを移動させず、成功メッセージを付けて再描画します
    
    # ページ再描画用のデータを再度取得
    user_settings = database.get_user_filter_settings(user_did)
    all_content_categories = llm_analyzer.CONTENT_CATEGORIES
    all_expression_categories = llm_analyzer.EXPRESSION_CATEGORIES
    all_style_stance_categories = llm_analyzer.STYLE_STANCE_CATEGORIES
    
    # settings.html を再度表示する
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "user_settings": user_settings,
            "all_content_categories": all_content_categories,
            "all_expression_categories": all_expression_categories,
            "all_style_stance_categories": all_style_stance_categories,
            "save_success": True  # 成功メッセージを表示するためのフラグ
        }
    )