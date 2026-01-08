
# Google Cloud Run へのデプロイ手順

このガイドでは、作成した `Dockerfile` を使用して、アプリケーションを Google Cloud Run にデプロイする手順を説明します。

## 前提条件

1.  **Google Cloud プロジェクト**が作成されていること。
2.  **課金**が有効になっていること。
3.  **Google Cloud CLI (gcloud)** がインストールされていること（または Cloud Shell を使用）。

## 手順

### 1. gcloud の初期設定 (初回のみ)

まだログインしていない場合は、以下のコマンドでログインし、プロジェクトを設定します。

```bash
gcloud auth login
gcloud config set project [あなたのプロジェクトID]
```
※ `[あなたのプロジェクトID]` は実際のプロジェクトIDに置き換えてください。

### 2. コンテナイメージのビルドと送信

Google Cloud Build を使って、Docker イメージをビルドし、Container Registry (または Artifact Registry) に保存します。

```bash
gcloud builds submit --tag gcr.io/[あなたのプロジェクトID]/inventory-check-tool
```

### 3. Cloud Run へデプロイ

ビルドしたイメージを Cloud Run にデプロイします。

```bash
gcloud run deploy inventory-check-tool \
  --image gcr.io/[あなたのプロジェクトID]/inventory-check-tool \
  --platform managed \
  --region asia-northeast1 \
  --allow-unauthenticated
```

- `--region asia-northeast1`: 東京リージョンを指定しています。変更も可能です。
- `--allow-unauthenticated`: 未認証のアクセスを許可します（Web公開用）。社内限定にする場合はこのオプションを外してください。

### 4. 完了

デプロイが成功すると、端末に URL が表示されます (例: `https://inventory-check-tool-xxxxx-an.a.run.app`)。
その URL にアクセスしてアプリが動作することを確認してください。

---

## 補足: ローカルでの動作確認 (Docker desktopが必要)

もしローカルPCに Docker がインストールされている場合、以下でテストできます。

```bash
docker build -t inventory-app .
docker run -p 8080:8080 inventory-app
```
ブラウザで `http://localhost:8080` にアクセス。
