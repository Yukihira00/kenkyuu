# check_tool.py
import uvicorn
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import numpy as np

app = FastAPI()

# 既存のCSSを流用するため、staticをマウント
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 採点対象のCSVファイル
CSV_FILE = 'analysis_for_checking_01.csv'
# 採点状況をチェックする列
CHECK_COLUMN = 'is_content_correct (0 or 1)'

def get_db():
    """CSVファイルをPandasで読み込む（簡易DBとして使用）"""
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
        # インデックスを振り直しておく
        df = df.reset_index()
        return df
    except FileNotFoundError:
        return None

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

    # 'is_content_correct (0 or 1)' の列が空（NaN）である最初の行を探す
    unscored_rows = db[db[CHECK_COLUMN].isna()]
    
    if unscored_rows.empty:
        # すべて採点済み
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

    # 採点するべき行データを取得
    next_row_index = unscored_rows.index[0]
    post_to_check = db.loc[next_row_index].to_dict()
    
    # 完了した件数を計算
    scored_count = len(db) - len(unscored_rows)
    total_count = len(db)
    progress_percent = (scored_count / total_count) * 100

    return templates.TemplateResponse("checker.html", {
        "request": request,
        "post": post_to_check,
        "index": next_row_index, # ◀ CSVの行インデックスを渡す
        "scored_count": scored_count,
        "total_count": total_count,
        "progress_percent": progress_percent
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
    判定結果（0 or 1）を受け取り、CSVに書き込んで次の投稿へリダイレクトする
    """
    if db is None:
        # CSVがない（通常は発生しない）
        return RedirectResponse(url="/", status_code=303)

    # 該当する行のインデックスを探す
    target_row_index = index
    
    if target_row_index in db.index:
        # 判定結果をDataFrameにセット
        db.at[target_row_index, 'is_content_correct (0 or 1)'] = content_score
        db.at[target_row_index, 'is_expression_correct (0 or 1)'] = expression_score
        db.at[target_row_index, 'is_style_correct (0 or 1)'] = style_score
        
        # 'index' 列を削除してCSVに保存
        db_to_save = db.drop(columns=['index'], errors='ignore')
        
        # CSVに上書き保存
        db_to_save.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

    # 次の未採点データを表示するためルートにリダイレクト
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    print(f"採点ツールを起動します。")
    print(f"CSV: {CSV_FILE}")
    print(f"URL: http://127.0.0.1:8000")
    uvicorn.run("check_tool:app", host="127.0.0.1", port=8000, reload=True)