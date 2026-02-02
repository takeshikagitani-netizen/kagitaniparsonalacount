# 領収書仕訳システム MVP

領収書や請求書の画像から自動で仕訳を生成するシステムです。

## 機能

- 領収書/請求書の画像アップロード（スマホ撮影対応）
- OCRによるテキスト抽出（Tesseract）
- データ自動抽出（日付、金額、取引先、摘要）
- ルールベースの仕訳案自動生成
- 仕訳一覧の確認・編集
- CSVエクスポート（汎用フォーマット）

## 技術スタック

- **バックエンド**: Python 3.10+ / FastAPI
- **フロントエンド**: HTML / Vanilla JavaScript（スマホ対応）
- **データベース**: SQLite
- **OCR**: Tesseract（pytesseract）

## セットアップ

### 必要条件

- Python 3.10以上
- Tesseract OCR（オプション：なくても動作可能）

### Tesseractのインストール（任意）

OCR機能を使用する場合は、Tesseractをインストールしてください。

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-jpn

# macOS
brew install tesseract tesseract-lang

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki からインストーラーをダウンロード
```

### 起動方法

#### 方法1: 起動スクリプトを使用（推奨）

```bash
chmod +x run.sh
./run.sh
```

#### 方法2: 手動セットアップ

```bash
# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r backend/requirements.txt

# 環境変数の設定
cp .env.example .env

# サーバー起動
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### アクセス

ブラウザで http://localhost:8000 を開きます。
スマホからアクセスする場合は、同じネットワーク内で `http://<PCのIPアドレス>:8000` にアクセスしてください。

## 使い方

### 1. 画像アップロード

1. 「アップロード」タブで領収書/請求書の画像を選択
2. 支払方法を選択
3. 「アップロードして解析」をクリック

### 2. テスト用ダミーデータ

画像なしでシステムをテストする場合：

1. 「テスト用ダミーデータ」セクションに情報を入力
2. 「ダミーデータで登録」をクリック

### 3. 仕訳の確認

1. 抽出データと仕訳案を確認
2. 問題なければ「確定」をクリック

### 4. CSV出力

1. 「仕訳一覧」タブを開く
2. 「CSV出力」ボタンをクリック

## CSVフォーマット

出力されるCSVは以下の形式です：

| 列名 | 説明 |
|------|------|
| 取引日 | YYYY-MM-DD形式 |
| 借方科目 | 勘定科目名 |
| 借方金額 | 金額（整数） |
| 貸方科目 | 勘定科目名 |
| 貸方金額 | 金額（整数） |
| 摘要 | 取引の説明 |
| 取引先 | 店名/社名 |
| 税区分 | 課税仕入/非課税仕入/不課税/対象外 |
| 支払方法 | クレジットカード/現金/銀行振込 |

## 勘定科目の初期セット

以下の勘定科目がデフォルトで利用可能です：

**借方科目（費用）**
- 旅費交通費
- 会議費
- 消耗品費
- 通信費
- 広告宣伝費
- 外注費
- 交際費
- 地代家賃
- 水道光熱費
- 新聞図書費
- 研修費
- 支払手数料
- 雑費

**貸方科目（支払手段）**
- 未払金（クレジットカード）
- 現金
- 普通預金

## API エンドポイント

| Method | Endpoint | 説明 |
|--------|----------|------|
| POST | /api/receipts/upload | 領収書アップロード |
| POST | /api/receipts/dummy | ダミーデータ作成 |
| GET | /api/receipts/ | 領収書一覧 |
| GET | /api/journals/ | 仕訳一覧 |
| PUT | /api/journals/{id} | 仕訳更新 |
| POST | /api/journals/{id}/confirm | 仕訳確定 |
| GET | /api/journals/export/csv | CSV出力 |
| GET | /api/journals/accounts | 勘定科目一覧 |

## 拡張ポイント

### OCRバックエンドの差し替え

`backend/app/services/ocr.py` で新しいバックエンドを実装できます：

```python
class GoogleVisionBackend(OCRBackend):
    def extract_text(self, image_path: str) -> str:
        # Google Cloud Vision API implementation
        pass
```

### LLMによる仕訳分類

`backend/app/services/journal_generator.py` でLLM連携を追加できます：

```python
# .env
USE_LLM_FOR_CLASSIFICATION=true
OPENAI_API_KEY=your-key
```

### 会計ソフト連携

CSVフォーマットをカスタマイズして各会計ソフトに対応可能：
- freee: `backend/app/routers/journals.py` の `export_csv` を拡張
- Money Forward: 同上
- 弥生: 同上

## ライセンス

MIT License

## 今後の予定

- [ ] LLMによる仕訳分類の精度向上
- [ ] 複数画像の一括アップロード
- [ ] freee API連携
- [ ] ユーザー認証
- [ ] 仕訳ルールのカスタマイズUI
