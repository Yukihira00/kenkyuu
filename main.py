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

    user_did = request.session['user_did']
    handle = request.session.get('user_handle')
    app_password = request.session.get('app_password')

    # --- 1. ユーザー情報を取得 ---
    display_name = request.session.get('user_display_name') or handle
    user_info = {
        "did": user_did,
        "handle": handle,
        "display_name": display_name
    }

    # --- 2. ユーザーのフィルター設定を取得 ---
    user_filter_settings = database.get_user_filter_settings(user_did)
    hidden_content = set(user_filter_settings.get('hidden_content_categories', []))
    hidden_expression = set(user_filter_settings.get('hidden_expression_categories', []))
    hidden_style = set(user_filter_settings.get('hidden_style_stance_categories', []))

    # --- 3. Blueskyからタイムラインを取得 ---
    # raw_feed の取得件数を調整可能（例: 50件に減らすなど）
    # LLM処理が増えるため、最初は少なめにするのがおすすめです
    raw_feed = timeline_checker.get_timeline_data(handle, app_password, limit=50) 

    if not raw_feed:
        return templates.TemplateResponse("timeline.html", {
            "request": request, "user": user_info, "feed": [],
            "hidden_post_count": 0, "total_post_count": 0
        })

    # --- 4. 投稿を分析・モザイクフラグを設定 ---
    processed_feed = [] # フィルタリング対象外も含む、処理済みのフィード
    hidden_post_count = 0
    total_post_count = len(raw_feed)

    for item in raw_feed:
        post_text = item.post.record.text
        
        # 投稿テキストが空の場合はモザイクなしでそのまま追加
        if not post_text.strip():
            # 日付形式を変換
            if isinstance(item.post.indexed_at, str):
                dt_str = item.post.indexed_at.replace('Z', '+00:00')
                item.post.indexed_at = datetime.fromisoformat(dt_str)
            item.is_mosaic = False
            item.analysis_info = None # 分析情報がないことを示す
            processed_feed.append(item)
            continue

        # LLMで投稿を分析
        analysis_result = llm_analyzer.analyze_post_text(post_text)
        
        item.is_mosaic = False # デフォルトはモザイクなし
        item.analysis_info = analysis_result # LLMの分析結果を保持
        
        if analysis_result:
            # いずれかのフィルターカテゴリに一致したらモザイクフラグを立てる
            if analysis_result.get("content_category") in hidden_content:
                item.is_mosaic = True
            if analysis_result.get("expression_category") in hidden_expression:
                item.is_mosaic = True
            if analysis_result.get("style_stance_category") in hidden_style:
                item.is_mosaic = True

        if item.is_mosaic:
            hidden_post_count += 1
        
        # 日付形式を変換（モザイク表示の有無にかかわらず行う）
        if isinstance(item.post.indexed_at, str):
            dt_str = item.post.indexed_at.replace('Z', '+00:00')
            item.post.indexed_at = datetime.fromisoformat(dt_str)
            
        processed_feed.append(item)

    # --- 5. テンプレートにデータを渡して表示 ---
    return templates.TemplateResponse("timeline.html", {
        "request": request,
        "user": user_info,
        "feed": processed_feed, # フィルタリング対象も含む全てを渡す
        "hidden_post_count": hidden_post_count,
        "total_post_count": total_post_count
    })

@app.get("/logout")
async def logout(request: Request):
    """
    ログアウト処理。セッションをクリアしてログインページに戻す。
    """
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


# main.py

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
    # ★★★ JavaScriptで使うため、必ず大文字のキーに変換します ★★★
    scores = {
        'H': result.get('h', 0), 'E': result.get('e', 0), 'X': result.get('x', 0),
        'A': result.get('a', 0), 'C': result.get('c', 0), 'O': result.get('o', 0)
    }

    # 整形したスコアと、性格の解説文をHTMLテンプレートに渡す
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