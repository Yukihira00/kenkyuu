FROM python:3.11-slim

WORKDIR /app

# 必要なツールをインストール
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 【重要】巨大なGPU版ではなく、軽量なCPU版のPyTorchを先にインストール
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# その他のライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリのコピー
COPY . .

# アプリ起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]