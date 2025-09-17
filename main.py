# main.py
from datetime import datetime
import secrets
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

import database, quiz_checker, timeline_checker, personality_descriptions, llm_analyzer, type_descriptions

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
templates = Jinja2Templates(directory="templates")

def get_64_type(scores: dict) -> str:
    mbti_type = ""
    mbti_type += "E" if scores.get('X', 0) >= 3.0 else "I"
    mbti_type += "N" if scores.get('O', 0) >= 3.0 else "S"
    mbti_type += "F" if scores.get('A', 0) >= 3.0 else "T"
    mbti_type += "J" if scores.get('C', 0) >= 3.0 else "P"
    turbulence_assertiveness = "T" if scores.get('E', 0) >= 3.0 else "A"
    light_dark = "L" if scores.get('H', 0) >= 3.0 else "D"
    return f"{mbti_type}-{turbulence_assertiveness}{light_dark}"

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login") if 'user_did' not in request.session else RedirectResponse(url="/timeline")

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_process(request: Request, handle: str = Form(...), app_password: str = Form(...)):
    user_profile = timeline_checker.verify_login_and_get_profile(handle, app_password)
    if user_profile:
        request.session['user_did'] = user_profile['did']
        request.session['handle'] = user_profile['handle']
        request.session['display_name'] = user_profile['display_name']
        request.session['app_password'] = app_password
        has_result = database.get_user_result(user_profile['did'])
        return RedirectResponse(url="/timeline", status_code=303) if has_result else RedirectResponse(url="/quiz", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": "ハンドルまたはアプリパスワードが間違っています。"})

@app.get("/quiz", response_class=HTMLResponse)
async def quiz_form(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    return templates.TemplateResponse("quiz.html", {"request": request, "questions": quiz_checker.QUESTIONS_DATA})

@app.post("/submit")
async def submit_quiz(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    form_data = await request.form()
    answers = [int(form_data[f'q{i}']) for i in range(1, len(quiz_checker.QUESTIONS_DATA) + 1) if f'q{i}' in form_data]
    if len(answers) == len(quiz_checker.QUESTIONS_DATA):
        scores = quiz_checker.calculate_scores(answers)
        database.add_or_update_hexaco_result(request.session['user_did'], request.session['handle'], scores)
        return RedirectResponse(url="/results", status_code=303)
    return templates.TemplateResponse("quiz.html", {"request": request, "questions": quiz_checker.QUESTIONS_DATA, "error": "すべての質問に回答してください。"})

@app.get("/timeline", response_class=HTMLResponse)
async def show_timeline(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    
    user_did = request.session['user_did']
    user_filter_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    hidden_content = set(user_filter_settings.get('hidden_content_categories', []))
    
    # ▼▼▼【変更】不快報告した投稿のURIリストを取得 ▼▼▼
    unpleasant_uris = set(database.get_unpleasant_feedback_uris(user_did))

    raw_feed = timeline_checker.get_timeline_data(request.session['handle'], request.session['app_password'], limit=50)
    if not raw_feed:
        return templates.TemplateResponse("timeline.html", {"request": request, "user": request.session, "feed": [], "hidden_post_count": 0, "total_post_count": 0, "user_settings": user_filter_settings, "analysis_results": {}})

    all_post_uris = [item.post.uri for item in raw_feed if item.post and item.post.uri]
    cached_results = database.get_cached_analysis_results(all_post_uris)
    
    posts_to_analyze = {
        item.post.uri: item.post.record.text.strip()
        for item in raw_feed
        if item.post.uri not in cached_results and hasattr(item.post.record, 'text') and item.post.record.text
    }

    if posts_to_analyze:
        uris_to_analyze = list(posts_to_analyze.keys())
        texts_to_analyze = list(posts_to_analyze.values())
        llm_results = llm_analyzer.analyze_posts_batch(texts_to_analyze)
        for uri, result in zip(uris_to_analyze, llm_results):
            if result:
                cached_results[uri] = result
                database.save_analysis_results(uri, result)

    processed_feed, hidden_post_count = [], 0
    for item in raw_feed:
        item.post.indexed_at = datetime.fromisoformat(item.post.indexed_at.replace('Z', '+00:00'))
        analysis_result = cached_results.get(item.post.uri)
        item.is_mosaic = False
        
        # ▼▼▼【変更】モザイク表示の条件に「不快報告」を追加 ▼▼▼
        if item.post.uri in unpleasant_uris:
            item.is_mosaic = True
            item.analysis_info = {"type": "不快な投稿", "category": "あなたが報告した投稿"}
        elif analysis_result:
            if analysis_result.get("content_category") in hidden_content:
                item.is_mosaic = True
                item.analysis_info = {"type": "コンテンツ", "category": analysis_result.get("content_category")}
            elif user_filter_settings.get('auto_filter_enabled') and user_scores:
                for trait, rules in personality_descriptions.FILTERING_RULES.items():
                    level = 'high' if user_scores[trait.lower()] >= 3.0 else 'low'
                    rule = rules[level]
                    post_category = analysis_result.get(f"{rule['type']}_category")
                    if post_category in rule['categories']:
                        item.is_mosaic = True
                        item.analysis_info = {"type": "性格診断", "category": post_category}
                        break
        
        if item.is_mosaic: hidden_post_count += 1
        processed_feed.append(item)

    return templates.TemplateResponse("timeline.html", {"request": request, "user": request.session, "feed": processed_feed, "hidden_post_count": hidden_post_count, "total_post_count": len(raw_feed), "user_settings": user_filter_settings, "analysis_results": cached_results})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

@app.get("/results", response_class=HTMLResponse)
async def show_results(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    result = database.get_user_result(request.session['user_did'])
    if not result: return RedirectResponse(url="/quiz")
    
    scores = { 'H': result.get('h',0), 'E': result.get('e',0), 'X': result.get('x',0), 'A': result.get('a',0), 'C': result.get('c',0), 'O': result.get('o',0) }
    type_info = type_descriptions.TYPE_DESCRIPTIONS.get(get_64_type(scores), {"title": "測定不能", "type_name": "不明", "description": "タイプを特定できませんでした。"})
    
    return templates.TemplateResponse("results.html", {"request": request, "scores": scores, "descriptions": personality_descriptions.DESCRIPTIONS, "type_info": type_info})

@app.get("/settings", response_class=HTMLResponse)
async def show_settings(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    
    user_did = request.session['user_did']
    user_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    active_rules = {}
    if user_scores:
        for trait, rules in personality_descriptions.FILTERING_RULES.items():
            level = 'high' if user_scores[trait.lower()] >= 3.0 else 'low'
            active_rules[rules['name']] = rules[level]['categories']
    
    return templates.TemplateResponse("settings.html", {"request": request, "user_settings": user_settings, "all_content_categories": llm_analyzer.CONTENT_CATEGORIES, "active_rules": active_rules})

@app.post("/settings")
async def save_settings(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    
    form_data = await request.form()
    hidden_content = form_data.getlist("hidden_content")
    auto_filter_enabled = form_data.get("auto_filter_switch") == "on"
    database.save_user_filter_settings(request.session['user_did'], hidden_content, auto_filter_enabled)
            
    return RedirectResponse(url="/settings", status_code=303)

class ReportPayload(BaseModel):
    uri: str

@app.post("/report_unpleasant")
async def report_unpleasant(request: Request, payload: ReportPayload):
    if 'user_did' not in request.session:
        return JSONResponse(content={"success": False, "error": "Not logged in"}, status_code=401)
    
    user_did = request.session['user_did']
    post_uri = payload.uri
    database.add_unpleasant_feedback(user_did, post_uri)
    return JSONResponse(content={"success": True})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)