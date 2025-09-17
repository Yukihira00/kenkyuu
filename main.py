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
import type_descriptions

# --- アプリケーションの初期設定 ---
app = FastAPI()

# セッション機能の追加 (ユーザーのログイン状態を記憶するため)
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))

# HTMLテンプレートを読み込む設定
templates = Jinja2Templates(directory="templates")


# --- タイプ分類ロジック ---
def get_64_type(scores: dict) -> str:
    """HEXACOの6つのスコアから新しい64タイプ分類の文字列を生成する"""
    
    mbti_type = ""
    mbti_type += "E" if scores.get('X', 0) >= 3.0 else "I"
    mbti_type += "N" if scores.get('O', 0) >= 3.0 else "S"
    mbti_type += "F" if scores.get('A', 0) >= 3.0 else "T"
    mbti_type += "J" if scores.get('C', 0) >= 3.0 else "P"
    
    turbulence_assertiveness = "T" if scores.get('E', 0) >= 3.0 else "A"
    light_dark = "L" if scores.get('H', 0) >= 3.0 else "D"
    
    return f"{mbti_type}-{turbulence_assertiveness}{light_dark}"

# --- ルート設定 ---

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

@app.get("/timeline", response_class=HTMLResponse)
async def show_timeline(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/timeline", status_code=302)

    user_did = request.session['user_did']
    handle = request.session.get('user_handle')
    app_password = request.session.get('app_password')

    user_info = {"did": user_did, "handle": handle, "display_name": request.session.get('user_display_name') or handle}
    user_filter_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    
    hidden_content = set(user_filter_settings.get('hidden_content_categories', []))

    raw_feed = timeline_checker.get_timeline_data(handle, app_password, limit=50) 
    if not raw_feed:
        return templates.TemplateResponse("timeline.html", {
            "request": request, "user": user_info, "feed": [], 
            "hidden_post_count": 0, "total_post_count": 0,
            "user_settings": user_filter_settings
        })

    all_post_uris = [item.post.uri for item in raw_feed if item.post and item.post.uri]
    cached_results = database.get_cached_analysis_results(all_post_uris)
    
    posts_to_analyze_map = {}
    for item in raw_feed:
        post_uri = item.post.uri
        post_text = item.post.record.text.strip() if hasattr(item.post.record, 'text') and item.post.record.text else ""
        if post_uri not in cached_results and post_text:
            posts_to_analyze_map[post_uri] = post_text

    if posts_to_analyze_map:
        uris_to_analyze = list(posts_to_analyze_map.keys())
        texts_to_analyze = list(posts_to_analyze_map.values())
        llm_results = llm_analyzer.analyze_posts_batch(texts_to_analyze)
        
        for i, uri in enumerate(uris_to_analyze):
            result = llm_results[i]
            if result:
                cached_results[uri] = result
                database.save_analysis_results(uri, result)

    processed_feed = []
    hidden_post_count = 0
    for item in raw_feed:
        if isinstance(item.post.indexed_at, str):
            dt_str = item.post.indexed_at.replace('Z', '+00:00')
            item.post.indexed_at = datetime.fromisoformat(dt_str)

        analysis_result = cached_results.get(item.post.uri)
        item.analysis_info = None
        item.is_mosaic = False
        
        if analysis_result:
            content_cat = analysis_result.get("content_category")
            
            # 1. コンテンツカテゴリによるフィルタリング
            if content_cat in hidden_content:
                item.is_mosaic = True
                item.analysis_info = {"type": "コンテンツ", "category": content_cat}

            # 2. 性格診断に基づく自動フィルタリング
            if not item.is_mosaic and user_filter_settings.get('auto_filter_enabled') and user_scores:
                for trait, rules in personality_descriptions.FILTERING_RULES.items():
                    score_key = trait.lower()
                    level = 'high' if user_scores[score_key] >= 3.0 else 'low'
                    
                    rule = rules[level]
                    target_category_type = rule['type']
                    target_categories = rule['categories']
                    
                    # 投稿の分析結果が、ルールのカテゴリタイプと一致するか確認
                    post_category = analysis_result.get(f"{target_category_type}_category")
                    
                    if post_category in target_categories:
                        item.is_mosaic = True
                        item.analysis_info = {"type": "性格診断", "category": post_category}
                        break # 一致したらループを抜ける
        
        if item.is_mosaic:
            hidden_post_count += 1

        processed_feed.append(item)

    return templates.TemplateResponse("timeline.html", {
        "request": request, "user": user_info, "feed": processed_feed,
        "hidden_post_count": hidden_post_count, "total_post_count": len(raw_feed),
        "user_settings": user_filter_settings,
        "analysis_results": cached_results # 全投稿の分析結果を渡す
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
    
    personality_type_64_code = get_64_type(scores)
    
    type_info = type_descriptions.TYPE_DESCRIPTIONS.get(personality_type_64_code, {
        "title": "測定不能", "type_name": "不明", "description": "タイプを特定できませんでした。"
    })

    return templates.TemplateResponse("results.html", {
        "request": request, "scores": scores, 
        "descriptions": personality_descriptions.DESCRIPTIONS, "type_info": type_info
    })

@app.get("/settings", response_class=HTMLResponse)
async def show_settings(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    user_did = request.session['user_did']
    user_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    
    active_rules = {}
    if user_scores:
        for trait, rules in personality_descriptions.FILTERING_RULES.items():
            score_key = trait.lower()
            level = 'high' if user_scores[score_key] >= 3.0 else 'low'
            active_rules[rules['name']] = rules[level]['categories']

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_settings": user_settings,
        "all_content_categories": llm_analyzer.CONTENT_CATEGORIES,
        "active_rules": active_rules
    })

@app.post("/settings")
async def save_settings(request: Request):
    if 'user_did' not in request.session:
        return RedirectResponse(url="/login", status_code=302)
    
    user_did = request.session['user_did']
    form_data = await request.form()
    
    hidden_content = form_data.getlist("hidden_content")
    auto_filter_enabled = form_data.get("auto_filter_switch") == "on"
    
    database.save_user_filter_settings(user_did, hidden_content, auto_filter_enabled)
    
    # 保存後に再度設定を読み込んで表示
    user_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    active_rules = {}
    if user_scores:
        for trait, rules in personality_descriptions.FILTERING_RULES.items():
            score_key = trait.lower()
            level = 'high' if user_scores[score_key] >= 3.0 else 'low'
            active_rules[rules['name']] = rules[level]['categories']
            
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "user_settings": user_settings,
        "all_content_categories": llm_analyzer.CONTENT_CATEGORIES,
        "active_rules": active_rules,
        "save_success": True
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)