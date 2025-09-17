# main.py
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
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))

# HTMLテンプレートを読み込む設定
templates = Jinja2Templates(directory="templates")


# --- ルート設定 (login, quiz, results, logout, settingsは変更なし) ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if 'user_did' in request.session:
        return RedirectResponse(url="/timeline", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login_process(request: Request, handle: str = Form(...), app_password: str = Form(...)):
    user_profile = timeline_checker.verify_login_and_get_profile(handle, app_password)

    if user_profile:
        request.session['user_did'] = user_profile['did']
        request.session['user_handle'] = user_profile['handle']
        request.session['user_display_name'] = user_profile['display_name']
        request.session['app_password'] = app_password

        result = database.get_user_result(user_profile['did'])
        if result:
            return RedirectResponse(url="/timeline", status_code=303)
        else:
            return RedirectResponse(url="/quiz", status_code=303)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "ハンドルまたはアプリパスワードが間違っています。"})


@app.get("/quiz", response_class=HTMLResponse)
async def quiz_form(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    questions = quiz_checker.QUESTIONS_DATA
    return templates.TemplateResponse("quiz.html", {"request": request, "questions": questions})


@app.post("/submit")
async def submit_quiz(request: Request):
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
        return RedirectResponse(url="/results", status_code=303)
    else:
        questions = quiz_checker.QUESTIONS_DATA
        return templates.TemplateResponse(
            "quiz.html", 
            {"request": request, "questions": questions, "error": "すべての質問に回答してください。"}
        )

# ★★★ /timeline の処理を全面的に変更 ★★★
@app.get("/timeline", response_class=HTMLResponse)
async def show_timeline(request: Request):
    """
    パーソナライズされたタイムラインを表示する（キャッシュ利用版）。
    """
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)

    user_did = request.session['user_did']
    handle = request.session.get('user_handle')
    app_password = request.session.get('app_password')

    # --- 1. ユーザー情報とフィルター設定を取得 ---
    user_info = {"did": user_did, "handle": handle, "display_name": request.session.get('user_display_name') or handle}
    user_filter_settings = database.get_user_filter_settings(user_did)
    hidden_content = set(user_filter_settings.get('hidden_content_categories', []))
    hidden_expression = set(user_filter_settings.get('hidden_expression_categories', []))
    hidden_style = set(user_filter_settings.get('hidden_style_stance_categories', []))

    # --- 2. Blueskyからタイムラインを取得 ---
    raw_feed = timeline_checker.get_timeline_data(handle, app_password, limit=50) 
    if not raw_feed:
        return templates.TemplateResponse("timeline.html", {"request": request, "user": user_info, "feed": [], "hidden_post_count": 0, "total_post_count": 0})

    # --- 3. キャッシュの確認と、未分析の投稿リスト作成 ---
    all_post_uris = [item.post.uri for item in raw_feed if item.post and item.post.uri]
    cached_results = database.get_cached_analysis_results(all_post_uris)
    
    posts_to_analyze_map = {} # {uri: text} の形式で未分析の投稿を保持
    for item in raw_feed:
        post_uri = item.post.uri
        post_text = item.post.record.text.strip() if item.post.record.text else ""
        if post_uri not in cached_results and post_text:
            posts_to_analyze_map[post_uri] = post_text

    # --- 4. 未分析の投稿があれば、まとめてLLMで分析 ---
    newly_analyzed_results = {}
    if posts_to_analyze_map:
        uris_to_analyze = list(posts_to_analyze_map.keys())
        texts_to_analyze = list(posts_to_analyze_map.values())
        
        llm_results = llm_analyzer.analyze_posts_batch(texts_to_analyze)
        
        for i, uri in enumerate(uris_to_analyze):
            result = llm_results[i]
            if result:
                newly_analyzed_results[uri] = result
                database.save_analysis_results(uri, result) # 結果をキャッシュに保存

    # --- 5. 全ての分析結果を統合 ---
    all_analysis_results = {**cached_results, **newly_analyzed_results}

    # --- 6. 投稿を処理し、分析結果をマッピング・モザイクフラグを設定 ---
    processed_feed = []
    hidden_post_count = 0
    for item in raw_feed:
        # 日付形式を変換
        if isinstance(item.post.indexed_at, str):
            dt_str = item.post.indexed_at.replace('Z', '+00:00')
            item.post.indexed_at = datetime.fromisoformat(dt_str)

        analysis_result = all_analysis_results.get(item.post.uri)
        item.analysis_info = analysis_result
        item.is_mosaic = False

        if analysis_result:
            if analysis_result.get("content_category") in hidden_content or \
               analysis_result.get("expression_category") in hidden_expression or \
               analysis_result.get("style_stance_category") in hidden_style:
                item.is_mosaic = True
        
        if item.is_mosaic:
            hidden_post_count += 1
            
        processed_feed.append(item)

    # --- 7. テンプレートにデータを渡して表示 ---
    return templates.TemplateResponse("timeline.html", {
        "request": request,
        "user": user_info,
        "feed": processed_feed,
        "hidden_post_count": hidden_post_count,
        "total_post_count": len(raw_feed)
    })


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.get("/results", response_class=HTMLResponse)
async def show_results(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    user_did = request.session['user_did']
    result = database.get_user_result(user_did)
    if not result:
        return RedirectResponse(url="/quiz", status_code=302)
    scores = {'H': result.get('h', 0), 'E': result.get('e', 0), 'X': result.get('x', 0), 'A': result.get('a', 0), 'C': result.get('c', 0), 'O': result.get('o', 0)}
    return templates.TemplateResponse("results.html", {"request": request, "scores": scores, "descriptions": personality_descriptions.DESCRIPTIONS})

@app.get("/settings", response_class=HTMLResponse)
async def show_settings(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    user_did = request.session['user_did']
    user_settings = database.get_user_filter_settings(user_did)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_settings": user_settings,
        "all_content_categories": llm_analyzer.CONTENT_CATEGORIES,
        "all_expression_categories": llm_analyzer.EXPRESSION_CATEGORIES,
        "all_style_stance_categories": llm_analyzer.STYLE_STANCE_CATEGORIES,
    })

@app.post("/settings")
async def save_settings(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    user_did = request.session['user_did']
    form_data = await request.form()
    
    hidden_content = form_data.getlist("hidden_content")
    hidden_expression = form_data.getlist("hidden_expression")
    hidden_style_stance = form_data.getlist("hidden_style_stance")
    
    database.save_user_filter_settings(user_did, hidden_content, hidden_expression, hidden_style_stance)
    
    user_settings = database.get_user_filter_settings(user_did)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_settings": user_settings,
        "all_content_categories": llm_analyzer.CONTENT_CATEGORIES,
        "all_expression_categories": llm_analyzer.EXPRESSION_CATEGORIES,
        "all_style_stance_categories": llm_analyzer.STYLE_STANCE_CATEGORIES,
        "save_success": True
    })