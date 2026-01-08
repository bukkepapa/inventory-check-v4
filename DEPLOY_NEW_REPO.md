# 新しいリポジトリへのデプロイ手順

Streamlit Cloud での `ModuleNotFoundError: No module named 'fitz'` エラーを解消するため、`requirements.txt` を修正しました。
以下の手順で新しい GitHub リポジトリを作成し、コードをプッシュしてください。

## 1. GitHub で新しいリポジトリを作成

1. GitHub にログインし、[新しいリポジトリの作成ページ](https://github.com/new) にアクセスします。
2. **Repository name** に以下の名前を入力してください（私が選定しました）:
   `inventory-check-v4`
3. "Public" または "Private" を選択します（Streamlit Cloud の無料枠なら Public 推奨ですが、機密データなら Private でも可）。
4. "Initialize this repository with..." のチェックは **全て外して** ください（空のリポジトリを作成）。
5. **Create repository** をクリックします。

## 2. コードをプッシュ

ターミナルで以下のコマンドを順番に実行して、新しいリポジトリにプッシュします。
※ `<あなたのGitHubユーザー名>` はご自身のユーザー名に置き換えてください。

```bash
# 新しいリモートURLを追加 (名前: v4)
git remote add v4 https://github.com/<あなたのGitHubユーザー名>/inventory-check-v4.git

# メインブランチを v4 リモートにプッシュ
git push -u v4 main
```

## 3. Streamlit Cloud でデプロイ

1. [Streamlit Cloud](https://share.streamlit.io/) にアクセスします。
2. **New app** をクリックします。
3. リポジトリ選択で `inventory-check-v4` を選びます。
4. Branch: `main`
5. Main file path: `app.py`
6. **Deploy!** をクリックします。

これで修正版の環境構築が行われ、エラーが解消されるはずです。
