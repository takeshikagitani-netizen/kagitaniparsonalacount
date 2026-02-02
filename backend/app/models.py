"""
データモデル定義
Firestoreドキュメントの構造を表現
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class JournalStatus(str, Enum):
    """仕訳のステータス"""
    PENDING = "pending"      # 未確定（OCR結果のまま）
    CONFIRMED = "confirmed"  # 確定済み（ユーザーが確認済み）


class TaxRate(int, Enum):
    """税率"""
    STANDARD = 10   # 標準税率 10%
    REDUCED = 8     # 軽減税率 8%
    EXEMPT = 0      # 非課税


# 勘定科目のリスト（借方）
DEBIT_ACCOUNTS = [
    "消耗品費",
    "旅費交通費",
    "交際費",
    "会議費",
    "通信費",
    "水道光熱費",
    "地代家賃",
    "広告宣伝費",
    "福利厚生費",
    "雑費",
    "仕入高",
    "外注費",
    "支払手数料",
]

# 勘定科目のリスト（貸方）
CREDIT_ACCOUNTS = [
    "現金",
    "普通預金",
    "クレジットカード",
    "未払金",
    "売掛金",
]


class JournalModel:
    """
    仕訳データモデル
    Firestoreドキュメントの構造
    """

    def __init__(
        self,
        id: str,
        user_id: str,
        date: str,
        amount: int,
        tax_rate: int,
        debit_account: str,
        credit_account: str,
        description: str,
        status: str = JournalStatus.PENDING.value,
        receipt_url: Optional[str] = None,
        receipt_filename: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.date = date
        self.amount = amount
        self.tax_rate = tax_rate
        self.debit_account = debit_account
        self.credit_account = credit_account
        self.description = description
        self.status = status
        self.receipt_url = receipt_url
        self.receipt_filename = receipt_filename
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        """Firestoreに保存する辞書形式に変換"""
        return {
            "user_id": self.user_id,
            "date": self.date,
            "amount": self.amount,
            "tax_rate": self.tax_rate,
            "debit_account": self.debit_account,
            "credit_account": self.credit_account,
            "description": self.description,
            "status": self.status,
            "receipt_url": self.receipt_url,
            "receipt_filename": self.receipt_filename,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, id: str, data: dict) -> "JournalModel":
        """Firestoreドキュメントからモデルを生成"""
        return cls(
            id=id,
            user_id=data.get("user_id", ""),
            date=data.get("date", ""),
            amount=data.get("amount", 0),
            tax_rate=data.get("tax_rate", 10),
            debit_account=data.get("debit_account", ""),
            credit_account=data.get("credit_account", ""),
            description=data.get("description", ""),
            status=data.get("status", JournalStatus.PENDING.value),
            receipt_url=data.get("receipt_url"),
            receipt_filename=data.get("receipt_filename"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


class UserModel:
    """
    ユーザーデータモデル
    Firestoreドキュメントの構造
    """

    def __init__(
        self,
        id: str,
        email: str,
        display_name: Optional[str] = None,
        photo_url: Optional[str] = None,
        role: str = "user",
        created_at: Optional[datetime] = None,
        last_login_at: Optional[datetime] = None,
    ):
        self.id = id
        self.email = email
        self.display_name = display_name
        self.photo_url = photo_url
        self.role = role
        self.created_at = created_at or datetime.utcnow()
        self.last_login_at = last_login_at or datetime.utcnow()

    def to_dict(self) -> dict:
        """Firestoreに保存する辞書形式に変換"""
        return {
            "email": self.email,
            "display_name": self.display_name,
            "photo_url": self.photo_url,
            "role": self.role,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
        }

    @classmethod
    def from_dict(cls, id: str, data: dict) -> "UserModel":
        """Firestoreドキュメントからモデルを生成"""
        return cls(
            id=id,
            email=data.get("email", ""),
            display_name=data.get("display_name"),
            photo_url=data.get("photo_url"),
            role=data.get("role", "user"),
            created_at=data.get("created_at"),
            last_login_at=data.get("last_login_at"),
        )
