# Python 3.10-slim をベースイメージとして使用
FROM python:3.9

# 作業ディレクトリを設定
WORKDIR /app

# システム依存関係をインストール (packages.txt の内容に基づく)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt をコピーして Python パッケージをインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# Streamlit のポート (8080) を公開
EXPOSE 8080

# アプリケーションの起動コマンド
# Cloud Run は PORT 環境変数 (デフォルト 8080) でリッスンすることを期待しています
CMD streamlit run app.py --server.port=8080 --server.address=0.0.0.0
