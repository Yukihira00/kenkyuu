# check_tool.py
import uvicorn
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import numpy as np
import llm_analyzer

# --- アプリケーションの定義 (必須) ---
app = FastAPI()

# 既存のCSSを流用するため、staticをマウント
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 採点対象のCSVファイル
CSV_FILE = 'analysis_for_checking_01.csv'
# 採点状況をチェックする列
CHECK_COLUMN = 'is_content_correct (0 or 1)'

# --- カテゴリのグループ化ロジック ---

# 表現/感情カテゴリをプルチックの感情の輪（画像）の構造に合わせてグループ化
def group_expression_categories(categories):
    # llm_analyzer.pyに定義されている全カテゴリを取得
    all_llm_cats = set(llm_analyzer.EXPRESSION_CATEGORIES)
    
    # 画像の構造 (8行 x 4列) に対応するリスト
    # 基本感情, 強い感情, 弱い感情, 反対の基本感情
    # このグリッドは、プルチックの感情の輪の構造（表示上の意図的な重複）を表現しています。
    # カテゴリリスト（`all_llm_cats`）側で重複が排除されているため、ここで重複していても問題ありません。
    expression_grid = [
        ["喜び", "恍惚", "平穏", "悲しみ"],
        ["期待", "警戒", "興味", "驚き"],
        ["怒り", "激怒", "煩さ", "恐れ"],
        ["嫌悪", "憎悪", "退屈", "信頼"],
        ["悲しみ", "悲痛", "憂い", "喜び"],
        ["驚き", "驚嘆", "動揺", "期待"],
        ["恐れ", "恐怖", "心配", "怒り"],
        ["信頼", "感嘆", "容認", "嫌悪"],
    ]
    
    # llm_analyzerに存在しないカテゴリは "-" で埋める処理
    final_grid = []
    for row in expression_grid:
        final_grid.append([cat if cat in all_llm_cats else '-' for cat in row])

    return final_grid

# スタイル/スタンスカテゴリをグループ化
def group_style_stance_categories(categories):
    # personality_descriptions.py のコメントに基づくグループ分け
    raw_groups = {
        "1. 優位・指導的": ["上から目線", "教訓的・啓発的", "皮肉・当てこすり", "恩着せがましい"],
        "2. 劣位・受動的": ["謙遜・へりくだった", "卑屈・自己卑下"],
        "3. 水平・中立・独白": ["丁寧・中立", "客観的・分析的", "冷淡・突き放す", "無関心・他人行儀", "独り言・独白"],
        "4. 協調・共感・ユーモア": ["共感的・寄り添う", "親しみを込めた", "激励・応援", "ユーモア・ネタ"],
        "5. 情熱・熱狂": ["情熱・熱狂"],
        "6. 対立・攻撃的": ["挑発的・攻撃的"],
    }
    
    # 実際に存在するカテゴリのみをフィルタリング
    unique_llm_cats = set(llm_analyzer.STYLE_STANCE_CATEGORIES)
    final_grouped_styles = {}
    for group_name, cats in raw_groups.items():
        # 順序を維持しつつフィルタリング
        filtered_cats = [c for c in cats if c in unique_llm_cats]
        if filtered_cats:
            final_grouped_styles[group_name] = filtered_cats
            
    return final_grouped_styles


# --- データベース接続 ---
def get_db():
    """CSVファイルをPandasで読み込む（簡易DBとして使用）"""
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
        # インデックスを振り直しておく
        df = df.reset_index()
        return df
    except FileNotFoundError:
        return None

# --- ルート定義 ---

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: pd.DataFrame = Depends(get_db)):
    """
    まだ採点されていない（空欄の）最初の行を見つけて表示する
    """
    if db is None:
        return templates.TemplateResponse("checker_error.html", {
            "request": request, 
            "error": f"{CSV_FILE} が見つかりません。"
        })

    # 未採点の行を探す
    unscored_rows = db[db[CHECK_COLUMN].isna()]
    
    if unscored_rows.empty:
        # すべて採点済みの場合
        total = len(db)
        content_acc = db['is_content_correct (0 or 1)'].mean()
        expression_acc = db['is_expression_correct (0 or 1)'].mean()
        style_acc = db['is_style_correct (0 or 1)'].mean()
        
        return templates.TemplateResponse("checker_complete.html", {
            "request": request,
            "total": total,
            "content_acc": content_acc * 100,
            "expression_acc": expression_acc * 100,
            "style_acc": style_acc * 100
        })

    # 採点対象のデータを取得
    next_row_index = unscored_rows.index[0]
    post_to_check = db.loc[next_row_index].to_dict()
    
    # 進捗計算
    scored_count = len(db) - len(unscored_rows)
    total_count = len(db)
    progress_percent = (scored_count / total_count) * 100

    # グループ化されたカテゴリデータを取得
    grouped_expression = group_expression_categories(llm_analyzer.EXPRESSION_CATEGORIES)
    grouped_style_stance = group_style_stance_categories(llm_analyzer.STYLE_STANCE_CATEGORIES)

    return templates.TemplateResponse("checker.html", {
        "request": request,
        "post": post_to_check,
        "index": next_row_index,
        "scored_count": scored_count,
        "total_count": total_count,
        "progress_percent": progress_percent,
        "expression_categories": grouped_expression, # テンプレートへ渡す
        "style_categories": grouped_style_stance,    # テンプレートへ渡す
    })

@app.post("/save_judgment")
async def save_judgment(
    request: Request,
    index: int = Form(...),
    content_score: int = Form(...),
    expression_score: int = Form(...),
    style_score: int = Form(...),
    db: pd.DataFrame = Depends(get_db)
):
    """
    判定結果を保存して次へ
    """
    if db is None:
        return RedirectResponse(url="/", status_code=303)

    target_row_index = index
    
    if target_row_index in db.index:
        # 判定結果を保存
        db.at[target_row_index, 'is_content_correct (0 or 1)'] = content_score
        db.at[target_row_index, 'is_expression_correct (0 or 1)'] = expression_score
        db.at[target_row_index, 'is_style_correct (0 or 1)'] = style_score
        
        # CSVに保存
        db_to_save = db.drop(columns=['index'], errors='ignore')
        db_to_save.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    print(f"採点ツールを起動します。")
    print(f"CSV: {CSV_FILE}")
    print(f"URL: http://127.0.0.1:8000")
    uvicorn.run("check_tool:app", host="127.0.0.1", port=8000, reload=True)