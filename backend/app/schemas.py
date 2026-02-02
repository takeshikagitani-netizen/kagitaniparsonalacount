"""
Pydantic スキーマ定義
APIリクエスト・レスポンスのバリデーション用
"""

from datetime import date, datetime
from typing import Optional, List

from pydantic import BaseModel, Field


# ===========================================
# 認証関連スキーマ
# ===========================================

class UserInfo(BaseModel):
    """ユーザー情報"""
    uid: str
    email: str
    display_name: Optional[str] = None
    photo_url: Optional[str] = None
    role: str = "user"


class TokenPayload(BaseModel):
    """トークンのペイロード"""
    uid: str
    email: Optional[str] = None


# ===========================================
# 仕訳関連スキーマ
# ===========================================

class JournalBase(BaseModel):
    """仕訳の基本スキーマ"""
    date: str = Field(..., description="仕訳日付 (YYYY-MM-DD)")
    amount: int = Field(..., ge=0, description="金額")
    tax_rate: int = Field(10, description="税率 (0, 8, 10)")
    debit_account: str = Field(..., description="借方科目")
    credit_account: str = Field(..., description="貸方科目")
    description: str = Field("", description="摘要")


class JournalCreate(JournalBase):
    """仕訳作成スキーマ（OCR結果から自動生成）"""
    pass


class JournalConfirm(JournalBase):
    """仕訳確定スキーマ（ユーザーが編集して確定）"""
    journal_id: str = Field(..., description="仕訳ID")


class JournalUpdate(BaseModel):
    """仕訳更新スキーマ"""
    date: Optional[str] = None
    amount: Optional[int] = None
    tax_rate: Optional[int] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    description: Optional[str] = None


class JournalResponse(JournalBase):
    """仕訳レスポンススキーマ"""
    id: str
    user_id: str
    status: str
    receipt_url: Optional[str] = None
    receipt_filename: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JournalListResponse(BaseModel):
    """仕訳一覧レスポンス"""
    journals: List[JournalResponse]
    total: int


# ===========================================
# アップロード関連スキーマ
# ===========================================

class UploadResponse(BaseModel):
    """アップロードレスポンススキーマ"""
    journal_id: str = Field(..., description="生成された仕訳ID")
    date: str = Field(..., description="OCRで抽出された日付")
    amount: int = Field(..., description="OCRで抽出された金額")
    tax_rate: int = Field(10, description="推定された税率")
    debit_account: str = Field(..., description="推定された借方科目")
    credit_account: str = Field("現金", description="デフォルトの貸方科目")
    description: str = Field("", description="OCRで抽出された摘要")
    receipt_url: Optional[str] = None


# ===========================================
# 共通レスポンススキーマ
# ===========================================

class MessageResponse(BaseModel):
    """メッセージレスポンス"""
    message: str
    status: str = "ok"


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    detail: str
    status: str = "error"
