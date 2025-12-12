# Dockerfile

# ベースイメージとしてPython 3.11を使用（main.pyのキャッシュファイル名から3.11/3.13と推測）
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なシステムパッケージをインストール（psycopg2などで必要になる場合があります）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ソースコードをコピー
COPY . .

# アプリケーションを実行（本番環境用設定）
# main.py内の if __name__ == "__main__": ブロックは直接実行時のみ動くため
# コマンドでuvicornを起動します
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]