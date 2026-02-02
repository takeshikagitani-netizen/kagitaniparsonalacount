# 領収書仕訳システム セットアップガイド

## 前提条件

- Python 3.9以上
- Node.js (任意: Live Serverを使用する場合)
- Firebaseプロジェクト（作成済み）
- Googleログインが有効化済み

---

## 1. Firebaseの設定

### 1.1 Firebase Consoleでの設定

1. [Firebase Console](https://console.firebase.google.com/) にアクセス
2. プロジェクトを選択

### 1.2 Webアプリの設定（フロントエンド用）

1. プロジェクト設定 → 全般 → マイアプリ
2. Webアプリを追加（または既存のアプリを選択）
3. Firebase SDK snippet の設定値をコピー
4. `frontend/index.html` の `firebaseConfig` を書き換え:

```javascript
const firebaseConfig = {
    apiKey: "あなたのAPIキー",
    authDomain: "あなたのプロジェクトID.firebaseapp.com",
    projectId: "あなたのプロジェクトID",
    storageBucket: "あなたのプロジェクトID.appspot.com",
    messagingSenderId: "あなたのSENDER_ID",
    appId: "あなたのAPP_ID"
};
```

### 1.3 サービスアカウントキーの取得（バックエンド用）

1. Firebase Console → プロジェクト設定 → サービスアカウント
2. 「新しい秘密鍵を生成」をクリック
3. JSONファイルがダウンロードされる
4. ファイル名を `serviceAccountKey.json` に変更
5. `backend/` フォルダに配置

### 1.4 Firestoreの設定

1. Firebase Console → Firestore Database
2. 「データベースを作成」（未作成の場合）
3. セキュリティルールを設定:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    match /journals/{journalId} {
      allow read, write: if request.auth != null
                         && resource.data.user_id == request.auth.uid;
      allow create: if request.auth != null
                    && request.resource.data.user_id == request.auth.uid;
    }
  }
}
```

---

## 2. バックエンドのセットアップ

```bash
# backendディレクトリに移動
cd backend

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt

# .envファイルを作成
cp .env.example .env

# .envファイルを編集（サービスアカウントキーのパスを確認）
# GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey.json
```

---

## 3. 起動方法

### 3.1 バックエンドの起動

```bash
cd backend

# 仮想環境を有効化（まだの場合）
source venv/bin/activate  # Mac/Linux
# または
venv\Scripts\activate  # Windows

# サーバーを起動
python run.py
```

サーバーが `http://localhost:8000` で起動します。

### 3.2 フロントエンドの起動

**方法A: Pythonの簡易サーバー**

```bash
cd frontend
python -m http.server 5500
```

**方法B: VS Code Live Server**

1. VS CodeでLive Server拡張機能をインストール
2. `frontend/index.html` を右クリック
3. 「Open with Live Server」を選択

**方法C: Node.js http-server**

```bash
npm install -g http-server
cd frontend
http-server -p 5500
```

フロントエンドが `http://localhost:5500` で起動します。

---

## 4. 動作確認

1. ブラウザで `http://localhost:5500` にアクセス
2. 「Googleでログイン」ボタンをクリック
3. Googleアカウントでログイン
4. 領収書画像をアップロード
5. 仕訳結果を確認・編集
6. 「仕訳を保存」をクリック
7. 仕訳一覧に表示されることを確認

---

## 5. Firebase Hostingへのデプロイ（本番公開）

### 5.1 Firebase CLIのインストール

```bash
npm install -g firebase-tools
```

### 5.2 Firebaseにログイン

```bash
firebase login
```

### 5.3 プロジェクトの初期化

```bash
firebase init hosting
```

- public ディレクトリ: `frontend`
- Single-page app: `No`
- GitHub自動デプロイ: `No`

### 5.4 デプロイ

```bash
firebase deploy --only hosting
```

### 5.5 本番用のCORS設定

`backend/app/main.py` の `allow_origins` に本番URLを追加:

```python
allow_origins=[
    "http://localhost:5500",
    "https://your-project-id.web.app",
    "https://your-project-id.firebaseapp.com",
],
```

---

## トラブルシューティング

### 「認証に失敗しました」と表示される

- Firebase Consoleで「Google」プロバイダが有効か確認
- `firebaseConfig` の値が正しいか確認

### 「無効なトークンです」と表示される

- `serviceAccountKey.json` が正しい場所にあるか確認
- バックエンドサーバーを再起動

### CORSエラーが発生する

- バックエンドの `allow_origins` にフロントエンドのURLを追加
- バックエンドサーバーを再起動

### Firestoreの権限エラー

- Firestoreのセキュリティルールを確認
- テスト用に一時的にルールを緩和して確認

---

## ファイル構成

```
kagitaniparsonalacount/
├── frontend/
│   ├── index.html          # フロントエンドUI
│   └── serve.py            # 開発サーバー
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPIアプリ
│   │   ├── database.py     # Firestore接続
│   │   ├── models.py       # データモデル
│   │   ├── schemas.py      # APIスキーマ
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py     # 認証ルーター
│   │   │   └── journals.py # 仕訳ルーター
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── firebase_service.py  # Firebase操作
│   │       └── ocr_service.py       # OCR処理
│   ├── requirements.txt    # Python依存関係
│   ├── run.py              # 起動スクリプト
│   ├── .env.example        # 環境変数サンプル
│   └── serviceAccountKey.json  # Firebase認証（要作成）
├── firestore.rules         # Firestoreセキュリティルール
├── .gitignore
└── SETUP.md               # このファイル
```
