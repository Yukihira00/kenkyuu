# main.py
from datetime import datetime
import secrets
from typing import List, Optional # 【修正】ここを追加しました
from fastapi.concurrency import run_in_threadpool
from fastapi import FastAPI, Request, Form, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
import numpy as np

# 自作モジュールのインポート
import database
import quiz_checker
import timeline_checker
import personality_descriptions
import llm_analyzer
import type_descriptions

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(SessionMiddleware, secret_key=secrets.token_hex(32))
templates = Jinja2Templates(directory="templates")

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def get_64_type(scores: dict) -> str:
    mbti_type = ""
    mbti_type += "E" if scores.get('X', 0) >= 3.0 else "I"
    mbti_type += "N" if scores.get('O', 0) >= 3.0 else "S"
    mbti_type += "F" if scores.get('A', 0) >= 3.0 else "T"
    mbti_type += "J" if scores.get('C', 0) >= 3.0 else "P"
    turbulence_assertiveness = "T" if scores.get('E', 0) >= 3.0 else "A"
    light_dark = "L" if scores.get('H', 0) >= 3.0 else "D"
    return f"{mbti_type}-{turbulence_assertiveness}{light_dark}"

# --- フィルタリングロジックを関数化 ---
def apply_filter_to_post(item, analysis_result, user_filter_settings, user_scores, unpleasant_uris, unpleasant_vectors):
    item.is_mosaic = False
    item.analysis_info = None

    SIMILARITY_THRESHOLD = user_filter_settings.get('similarity_threshold', 0.80)
    hidden_content_manual = set(user_filter_settings.get('hidden_content_categories', []))
    strength = user_filter_settings.get('filter_strength', 2)

    if item.post.uri in unpleasant_uris:
        item.is_mosaic = True
        item.analysis_info = {"type": "不快な投稿", "category": "あなたが報告した投稿"}
        return item

    if not analysis_result:
        return item

    post_embedding = analysis_result.get("embedding")
    is_similar = False
    if post_embedding is not None and unpleasant_vectors:
        for unpleasant_vec in unpleasant_vectors:
            similarity = cosine_similarity(post_embedding, unpleasant_vec)
            if similarity > SIMILARITY_THRESHOLD:
                is_similar = True
                break
    
    if user_filter_settings.get('similarity_filter_enabled') and is_similar:
        item.is_mosaic = True
        item.analysis_info = {"type": "類似フィルター", "category": "あなたが不快と報告した投稿に類似"}
    elif analysis_result.get("content_category") in hidden_content_manual:
        item.is_mosaic = True
        item.analysis_info = {"type": "手動フィルター", "category": analysis_result.get("content_category")}
    elif user_filter_settings.get('auto_filter_enabled') and user_scores:
        for trait, rules_by_level in personality_descriptions.FILTERING_RULES.items():
            level = 'high' if user_scores.get(trait.lower(), 0) >= 3.0 else 'low'
            rule_list = rules_by_level.get(level, [])
            for rule in rule_list:
                categories_to_hide = rule['categories'].get(strength, [])
                category_key = ""
                if rule['type'] == 'style': category_key = 'style_stance_category'
                elif rule['type'] == 'expression': category_key = 'expression_category'
                elif rule['type'] == 'content': category_key = 'content_category'

                if category_key:
                    post_category = analysis_result.get(category_key)
                    if post_category in categories_to_hide:
                        item.is_mosaic = True
                        item.analysis_info = {"type": "性格診断フィルター", "category": post_category}
                        break
            if item.is_mosaic: break
    
    return item

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login") if 'user_did' not in request.session else RedirectResponse(url="/timeline")

@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/app_password_info", response_class=HTMLResponse)
async def app_password_info(request: Request):
    return templates.TemplateResponse("app_password_info.html", {"request": request})

@app.post("/login")
async def login_process(request: Request, handle: str = Form(...), app_password: str = Form(...)):
    user_profile = timeline_checker.verify_login_and_get_profile(handle, app_password)
    if user_profile:
        request.session['user_did'] = user_profile['did']
        request.session['handle'] = user_profile['handle']
        request.session['display_name'] = user_profile.get('display_name') or user_profile.get('handle')
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
    return templates.TemplateResponse("timeline.html", {"request": request, "user": request.session})

@app.get("/timeline_content", response_class=HTMLResponse)
async def get_timeline_content(request: Request, cursor: str = None, feed_type: str = 'search'):
    if 'user_did' not in request.session: return HTMLResponse("セッション切れです。再ログインしてください。", status_code=403)

    user_did = request.session['user_did']
    
    user_filter_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    unpleasant_uris = set(database.get_unpleasant_feedback_uris(user_did))
    unpleasant_vectors = database.get_unpleasant_post_vectors(user_did)
    
    raw_feed, next_cursor = await run_in_threadpool(
        timeline_checker.get_timeline_data,
        request.session['handle'], 
        request.session['app_password'], 
        limit=100, 
        cursor=cursor,
        feed_type=feed_type
    )
    
    if not raw_feed:
        return templates.TemplateResponse("timeline_items.html", {"request": request, "feed": [], "hidden_post_count": 0, "total_post_count": 0, "analysis_results": {}, "next_cursor": None})

    all_post_uris = [item.post.uri for item in raw_feed if item.post and item.post.uri]
    cached_results = database.get_cached_analysis_results(all_post_uris)
    
    processed_feed, hidden_post_count = [], 0
    for item in raw_feed:
        if isinstance(item.post.indexed_at, str):
            item.post.indexed_at = datetime.fromisoformat(item.post.indexed_at.replace('Z', '+00:00'))
            
        analysis_result = cached_results.get(item.post.uri)
        item.is_mosaic = False
        item.analysis_info = None
        item.needs_analysis = False

        if analysis_result or (item.post.uri in unpleasant_uris):
            apply_filter_to_post(item, analysis_result, user_filter_settings, user_scores, unpleasant_uris, unpleasant_vectors)
            if item.is_mosaic: hidden_post_count += 1
        else:
            item.needs_analysis = True
        
        processed_feed.append(item)

    return templates.TemplateResponse("timeline_items.html", {
        "request": request, 
        "feed": processed_feed, 
        "hidden_post_count": hidden_post_count,
        "total_post_count": len(raw_feed), 
        "analysis_results": cached_results,
        "next_cursor": next_cursor
    })

# --- バッチ分析API ---
class PostItem(BaseModel):
    uri: str
    text: str

class AnalyzeBatchPayload(BaseModel):
    items: List[PostItem] # 【修正】List型ヒントを使用

@app.post("/api/analyze_posts_batch")
async def analyze_batch_posts_api(request: Request, payload: AnalyzeBatchPayload):
    if 'user_did' not in request.session: return JSONResponse(content={"error": "Not logged in"}, status_code=401)
    
    user_did = request.session['user_did']
    
    texts = [item.text for item in payload.items]
    uris = [item.uri for item in payload.items]
    
    if not texts:
        return JSONResponse(content={"results": []})

    # Gemini API呼び出し
    llm_results = await run_in_threadpool(llm_analyzer.analyze_posts_batch, texts)
    
    user_filter_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    unpleasant_uris = set(database.get_unpleasant_feedback_uris(user_did))
    unpleasant_vectors = database.get_unpleasant_post_vectors(user_did)
    
    response_results = []
    
    for i, result in enumerate(llm_results):
        uri = uris[i]
        
        if result:
            database.save_analysis_results(uri, result)
        
        class DummyPost: uri = ""
        class DummyItem:
            post = DummyPost()
            is_mosaic = False
            analysis_info = None
        
        dummy_item = DummyItem()
        dummy_item.post.uri = uri
        
        apply_filter_to_post(dummy_item, result, user_filter_settings, user_scores, unpleasant_uris, unpleasant_vectors)
        
        response_results.append({
            "uri": uri,
            "success": True,
            "is_mosaic": dummy_item.is_mosaic,
            "analysis_info": dummy_item.analysis_info,
            "analysis_result": result
        })
    
    return JSONResponse(content={"results": response_results})

# ... (ログアウト以下のコードは既存と同じ) ...
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
    type_code = get_64_type(scores)
    type_info = type_descriptions.TYPE_DESCRIPTIONS.get(type_code, {"title": "測定不能", "type_name": "不明", "description": "タイプを特定できませんでした。"})
    return templates.TemplateResponse("results.html", {"request": request, "scores": scores, "descriptions": personality_descriptions.DESCRIPTIONS, "type_info": type_info, "type_code": type_code})

@app.get("/settings", response_class=HTMLResponse)
async def show_settings(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    user_did = request.session['user_did']
    user_settings = database.get_user_filter_settings(user_did)
    user_scores = database.get_user_result(user_did)
    active_rules = {}
    if user_scores:
        strength = user_settings.get('filter_strength', 2)
        for trait, rules_by_level in personality_descriptions.FILTERING_RULES.items():
            level = 'high' if user_scores.get(trait.lower(), 0) >= 3.0 else 'low'
            rule_list = rules_by_level.get(level, [])
            merged_categories = []
            for rule in rule_list:
                merged_categories.extend(rule['categories'].get(strength, []))
            if merged_categories:
                active_rules[rules_by_level['name']] = list(set(merged_categories))
    return templates.TemplateResponse("settings.html", {"request": request, "user_settings": user_settings, "all_content_categories": llm_analyzer.CONTENT_CATEGORIES, "active_rules": active_rules})

@app.post("/settings")
async def save_settings(request: Request):
    if 'user_did' not in request.session: return RedirectResponse(url="/login")
    form_data = await request.form()
    hidden_content = form_data.getlist("hidden_content")
    auto_filter_enabled = form_data.get("auto_filter_switch") == "on"
    similarity_filter_enabled = form_data.get("similarity_filter_switch") == "on"
    filter_strength = int(form_data.get("filter_strength", 2))
    similarity_threshold = float(form_data.get("similarity_threshold", 0.80))
    
    database.save_user_filter_settings(request.session['user_did'], hidden_content, auto_filter_enabled, similarity_filter_enabled, filter_strength, similarity_threshold)
    
    user_settings = database.get_user_filter_settings(request.session['user_did'])
    user_scores = database.get_user_result(request.session['user_did'])
    active_rules = {}
    if user_scores:
        strength = user_settings.get('filter_strength', 2)
        for trait, rules_by_level in personality_descriptions.FILTERING_RULES.items():
            level = 'high' if user_scores.get(trait.lower(), 0) >= 3.0 else 'low'
            rule_list = rules_by_level.get(level, [])
            merged_categories = []
            for rule in rule_list:
                merged_categories.extend(rule['categories'].get(strength, []))
            if merged_categories:
                active_rules[rules_by_level['name']] = list(set(merged_categories))
    return templates.TemplateResponse("settings.html", {"request": request, "user_settings": user_settings, "all_content_categories": llm_analyzer.CONTENT_CATEGORIES, "active_rules": active_rules, "save_success": True})

class ReportPayload(BaseModel):
    uri: str
class FeedbackPayload(BaseModel):
    uri: str
    filter_type: str
    feedback: str

@app.post("/report_filter_feedback")
async def report_filter_feedback(request: Request, payload: FeedbackPayload):
    if 'user_did' not in request.session: return JSONResponse(content={"success": False, "error": "Not logged in"}, status_code=401)
    database.add_filter_feedback(user_did=request.session['user_did'], post_uri=payload.uri, filter_type=payload.filter_type, feedback=payload.feedback)
    return JSONResponse(content={"success": True})

@app.post("/report_unpleasant")
async def report_unpleasant(request: Request, payload: ReportPayload):
    if 'user_did' not in request.session: return JSONResponse(content={"success": False, "error": "Not logged in"}, status_code=401)
    user_did = request.session['user_did']
    database.add_unpleasant_feedback(user_did, payload.uri)
    return JSONResponse(content={"success": True})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)