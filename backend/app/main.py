"""
領収書仕訳システム - メインアプリケーション
FastAPI バックエンド
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, journals

# FastAPI アプリケーション作成
app = FastAPI(
    title="領収書仕訳システム API",
    description="領収書をアップロードして仕訳を生成・管理するAPIです",
    version="1.0.0"
)

# CORS設定（フロントエンドからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        # Firebase Hosting用（デプロイ後に追加）
        # "https://your-project-id.web.app",
        # "https://your-project-id.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを登録
app.include_router(auth.router, prefix="/api", tags=["認証"])
app.include_router(journals.router, prefix="/api", tags=["仕訳"])


@app.get("/")
async def root():
    """ヘルスチェック用エンドポイント"""
    return {
        "status": "ok",
        "message": "領収書仕訳システム API is running",
        "version": "1.0.0"
    }


@app.get("/api/dummy")
async def dummy():
    """開発用ダミーエンドポイント（認証不要）"""
    return {
        "status": "ok",
        "message": "Dummy API is working",
        "data": {
            "sample_journal": {
                "date": "2024-01-15",
                "amount": 1980,
                "tax_rate": 10,
                "debit_account": "消耗品費",
                "credit_account": "現金",
                "description": "文房具購入"
            }
        }
    }
