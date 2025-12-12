FROM python:3.11-slim

WORKDIR /app

# 必要なツールをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 軽量なCPU版のPyTorchをインストール
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# その他のライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリのコピー
COPY . .

# 【ここが修正点】作業場所を app フォルダの中に変更します
WORKDIR /app/app

# 【ここも修正点】app.main ではなく main:app に変更します
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]