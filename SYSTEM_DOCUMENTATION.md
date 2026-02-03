# 領収書仕訳システム - 技術仕様書

## 1. システム概要

### 1.1 目的
領収書の画像をOCR（光学文字認識）で自動解析し、仕訳データとして管理・出力するWebアプリケーション。

### 1.2 主な利用シーン
- 個人事業主・中小企業の経理業務
- 税理士への提出用データ作成
- インボイス制度対応の領収書管理

### 1.3 システムURL
- **本番環境**: https://receipt-journal-bb6aa.web.app
- **利用マニュアル**: https://receipt-journal-bb6aa.web.app/user-manual.html
- **APIキー設定マニュアル**: https://receipt-journal-bb6aa.web.app/api-manual.html

---

## 2. 技術スタック

### 2.1 フロントエンド
| 技術 | 用途 |
|------|------|
| HTML5 | 構造 |
| CSS3 | スタイリング（レスポンシブ対応） |
| JavaScript (ES6+) | ロジック・DOM操作 |
| Google Fonts (Noto Sans JP) | 日本語フォント |

### 2.2 バックエンド・インフラ
| サービス | 用途 |
|----------|------|
| Firebase Authentication | ユーザー認証（Google OAuth） |
| Cloud Firestore | NoSQLデータベース |
| Firebase Hosting | 静的ファイルホスティング |
| Google Cloud Vision API | OCR（文字認識） |

### 2.3 外部API
| API | 用途 | 料金 |
|-----|------|------|
| Google Cloud Vision API | 領収書画像のテキスト抽出 | 月1,000枚まで無料、以降$1.50/1,000枚 |

---

## 3. ファイル構成

```
kagitaniparsonalacount/
├── frontend/
│   ├── index.html          # メインアプリケーション（2,530行）
│   ├── user-manual.html    # 利用者向けマニュアル
│   └── api-manual.html     # APIキー設定マニュアル
├── firestore.rules         # Firestoreセキュリティルール
├── firebase.json           # Firebase設定ファイル
└── SYSTEM_DOCUMENTATION.md # 本ドキュメント
```

---

## 4. データベース設計（Firestore）

### 4.1 コレクション構造

#### journals（仕訳データ）
```javascript
{
  user_id: "string",              // FirebaseユーザーUID
  date: "YYYY-MM-DD",             // 取引日付
  amount: number,                  // 金額（整数）
  tax_rate: number,                // 税率（10, 8, 0）
  debit_account: "string",         // 借方科目
  credit_account: "string",        // 貸方科目
  description: "string",           // 摘要
  vendor_name: "string",           // 社名・店舗名
  registration_number: "string",   // インボイス登録番号（T+13桁）
  receipt_filename: "string",      // 元ファイル名
  status: "confirmed" | "pending", // ステータス
  created_at: Timestamp,           // 作成日時
  updated_at: Timestamp            // 更新日時
}
```

#### user_settings（ユーザー設定）
```javascript
{
  apiKey: "string",           // Google Cloud Vision APIキー
  updated_at: Timestamp       // 更新日時
}
```

### 4.2 セキュリティルール（firestore.rules）
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 仕訳データ: 自分のデータのみ読み書き可能
    match /journals/{journalId} {
      allow read, write: if request.auth != null
        && request.auth.uid == resource.data.user_id;
      allow create: if request.auth != null
        && request.auth.uid == request.resource.data.user_id;
    }

    // ユーザー設定: 自分の設定のみ読み書き可能
    match /user_settings/{userId} {
      allow read, write: if request.auth != null
        && request.auth.uid == userId;
    }
  }
}
```

---

## 5. 機能詳細

### 5.1 認証機能

#### Googleログイン
```javascript
// ポップアップ認証（デスクトップ向け）
await auth.signInWithPopup(provider);

// リダイレクト認証（モバイル向けフォールバック）
await auth.signInWithRedirect(provider);
```

**対応ケース**:
- ポップアップブロック時は自動的にリダイレクト認証に切り替え
- iOSのSafariでも動作

### 5.2 OCR機能

#### 処理フロー
1. ユーザーが画像をアップロード（またはカメラ撮影）
2. 画像をBase64エンコード
3. Google Cloud Vision APIにPOSTリクエスト
4. レスポンスからテキストを抽出
5. 正規表現でデータを解析

#### Vision API リクエスト
```javascript
const requestBody = {
  requests: [{
    image: { content: base64Image },
    features: [{ type: 'TEXT_DETECTION', maxResults: 1 }]
  }]
};

const response = await fetch(
  `https://vision.googleapis.com/v1/images:annotate?key=${userApiKey}`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  }
);
```

#### テキスト解析パターン

**日付抽出**:
```javascript
// 対応形式
/(\d{4})[\/\-年](\d{1,2})[\/\-月](\d{1,2})/  // 2024/01/15, 2024年1月15日
/令和\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)/     // 令和6年1月15日
/R(\d+)[\.\/](\d+)[\.\/](\d+)/               // R6.1.15
```

**金額抽出**:
```javascript
/合計[^\d]*[¥￥]?\s*([\d,]+)/i   // 合計 ¥1,234
/[¥￥]\s*([\d,]+)/               // ¥1,234
/(\d{1,3}(?:,\d{3})+)円/         // 1,234円
```

**インボイス登録番号**:
```javascript
/T\d{13}/  // T1234567890123
```

**勘定科目の自動推定**:
| キーワード | 推定科目 |
|------------|----------|
| タクシー、電車、交通 | 旅費交通費 |
| カフェ、コーヒー、会議 | 会議費 |
| 接待、贈答 | 交際費 |
| 電話、通信 | 通信費 |
| 電気、ガス、水道 | 水道光熱費 |
| 文具、事務 | 消耗品費 |

### 5.3 カメラ撮影機能

```html
<input type="file"
       id="cameraInput"
       accept="image/*"
       capture="environment">
```

- `capture="environment"`: 背面カメラを優先起動
- `accept="image/*"`: 画像ファイルのみ許可
- モバイルデバイスで撮影後、自動的にOCR処理開始

### 5.4 CSV出力機能

```javascript
// BOM付きUTF-8でExcel互換性を確保
const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
const blob = new Blob([bom, csvContent], {
  type: 'text/csv;charset=utf-8;'
});
```

**出力カラム**:
1. 日付
2. 借方科目
3. 貸方科目
4. 金額
5. 税区分
6. 摘要
7. 社名
8. 登録番号
9. ファイル名
10. ステータス

### 5.5 レスポンシブデザイン

#### ブレークポイント
| 幅 | 対象デバイス |
|----|--------------|
| > 768px | デスクトップ・タブレット |
| ≤ 768px | スマートフォン |
| ≤ 480px | 小型スマートフォン |

#### モバイル最適化
- 仕訳一覧: テーブル → カード形式に変換
- ボタン: タッチしやすいサイズに拡大
- 入力欄: font-size 16px以上（iOS拡大防止）

---

## 6. セキュリティ

### 6.1 認証
- Firebase Authentication による Google OAuth 2.0
- セッショントークンは自動管理

### 6.2 データ保護
- Firestoreセキュリティルールで自分のデータのみアクセス可能
- APIキーはユーザーごとに個別保存（共有しない）

### 6.3 APIキー管理
- 各ユーザーが自身のGoogle Cloud Vision APIキーを登録
- キーは `user_settings` コレクションに暗号化保存
- 他ユーザーからはアクセス不可

### 6.4 注意事項
- 領収書画像はサーバーに保存されない（OCR処理のみ）
- 元画像はユーザー側で別途管理が必要（Googleドライブ推奨）

---

## 7. API利用料金

### Google Cloud Vision API

| 使用量 | 料金 |
|--------|------|
| 月0〜1,000枚 | **無料** |
| 月1,001〜5,000,000枚 | $1.50/1,000枚（約0.2円/枚） |

**重要**: 各ユーザーが自身のAPIキーを使用するため、無料枠はユーザーごとに適用される。

### 料金シミュレーション
| 利用者 | 月間枚数 | 料金 |
|--------|----------|------|
| クライアントA | 100枚 | 無料 |
| クライアントB | 200枚 | 無料 |
| クライアントC | 500枚 | 無料 |
| **合計** | **800枚** | **無料** |

（各クライアントが自身のAPIキーを使用する場合）

---

## 8. デプロイ方法

### 8.1 Firebase CLI インストール
```bash
npm install -g firebase-tools
```

### 8.2 ログイン
```bash
firebase login
```

### 8.3 デプロイ
```bash
# ホスティングのみ
firebase deploy --only hosting

# Firestoreルールのみ
firebase deploy --only firestore:rules

# すべて
firebase deploy
```

### 8.4 firebase.json 設定
```json
{
  "hosting": {
    "public": "frontend",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [{"source": "**", "destination": "/index.html"}]
  },
  "firestore": {
    "rules": "firestore.rules"
  }
}
```

---

## 9. ワークフロー

### 9.1 スマートフォンで直接処理（推奨）
```
1. アプリを開く
   ↓
2. 「カメラで撮影」ボタンをタップ
   ↓
3. 領収書を撮影
   ↓
4. 自動OCR解析
   ↓
5. 仕訳内容を確認・修正
   ↓
6. 「保存」ボタン
   ↓
7. CSVダウンロード（月末など）
```

### 9.2 PCでまとめて処理
```
1. スマホで領収書を撮影
   ↓
2. Googleドライブに保存
   ↓
3. PCでアプリを開く
   ↓
4. 複数ファイルをドラッグ&ドロップ
   ↓
5. 「すべて処理開始」
   ↓
6. 1枚ずつ確認・保存
   ↓
7. CSVダウンロード
```

---

## 10. 勘定科目一覧

### 借方科目（経費）
| 科目名 | 用途例 |
|--------|--------|
| 消耗品費 | 文房具、日用品 |
| 旅費交通費 | 電車、タクシー、駐車場 |
| 交際費 | 接待、贈答品 |
| 会議費 | 会議時の飲食代 |
| 通信費 | 電話、インターネット |
| 水道光熱費 | 電気、ガス、水道 |
| 地代家賃 | 事務所賃料 |
| 広告宣伝費 | 広告、宣伝 |
| 福利厚生費 | 従業員向け福利 |
| 雑費 | その他 |

### 貸方科目（支払方法）
| 科目名 | 用途 |
|--------|------|
| 現金 | 現金払い |
| 普通預金 | 銀行振込 |
| クレジットカード | カード払い |
| 未払金 | 後払い |

---

## 11. トラブルシューティング

### 11.1 OCRが動作しない
- **原因**: APIキー未設定または無効
- **対処**: 設定画面からAPIキーを確認・再設定

### 11.2 ログインできない
- **原因**: ポップアップブロック
- **対処**: ブラウザ設定でポップアップを許可、または自動リダイレクト認証を待つ

### 11.3 仕訳が保存できない
- **原因**: ネットワークエラーまたはFirestoreルール
- **対処**: ネットワーク接続を確認、ページをリロード

### 11.4 カメラが起動しない
- **原因**: ブラウザのカメラ権限
- **対処**: ブラウザ設定でカメラへのアクセスを許可

---

## 12. 今後の拡張案

### 短期
- [ ] 仕訳のフィルタリング・検索機能
- [ ] 期間指定でのCSV出力
- [ ] 仕訳テンプレート機能

### 中期
- [ ] 会計ソフト連携（freee, MoneyForward）
- [ ] 領収書画像のクラウド保存
- [ ] 複数事業者の切り替え

### 長期
- [ ] AI による勘定科目の学習・最適化
- [ ] レポート・集計機能
- [ ] 税理士向け共有機能

---

## 13. Firebase プロジェクト情報

| 項目 | 値 |
|------|-----|
| プロジェクトID | receipt-journal-bb6aa |
| リージョン | us-central1（デフォルト） |
| 認証プロバイダ | Google |
| データベース | Firestore (Native mode) |

### Firebase Console
https://console.firebase.google.com/project/receipt-journal-bb6aa

---

## 14. 連絡先・サポート

- **GitHub Issues**: バグ報告・機能要望
- **マニュアル**: https://receipt-journal-bb6aa.web.app/user-manual.html

---

**最終更新日**: 2026年2月3日
**バージョン**: 1.0.0
