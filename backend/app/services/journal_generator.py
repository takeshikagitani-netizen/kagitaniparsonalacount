"""Journal entry generation service.

Generates accounting journal entries (仕訳) based on:
1. Rule-based keyword matching (default)
2. LLM-based classification (optional, future)
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
import logging

from ..models import AccountMapping

logger = logging.getLogger(__name__)


@dataclass
class JournalSuggestion:
    """Suggested journal entry."""
    debit_account: str  # 借方科目
    credit_account: str  # 貸方科目
    tax_category: str  # 税区分
    confidence: float  # 0.0 - 1.0


# Default account mappings (keyword -> account)
DEFAULT_MAPPINGS: List[Tuple[str, str, str]] = [
    # (keyword, account_name, tax_category)
    # 旅費交通費
    ("タクシー", "旅費交通費", "課税仕入"),
    ("交通", "旅費交通費", "課税仕入"),
    ("JR", "旅費交通費", "課税仕入"),
    ("電車", "旅費交通費", "課税仕入"),
    ("新幹線", "旅費交通費", "課税仕入"),
    ("航空", "旅費交通費", "課税仕入"),
    ("飛行機", "旅費交通費", "課税仕入"),
    ("Suica", "旅費交通費", "課税仕入"),
    ("PASMO", "旅費交通費", "課税仕入"),
    ("駐車", "旅費交通費", "課税仕入"),
    ("ガソリン", "旅費交通費", "課税仕入"),
    ("高速", "旅費交通費", "課税仕入"),

    # 会議費
    ("会議", "会議費", "課税仕入"),
    ("ミーティング", "会議費", "課税仕入"),
    ("カフェ", "会議費", "課税仕入"),
    ("コーヒー", "会議費", "課税仕入"),
    ("スターバックス", "会議費", "課税仕入"),
    ("ドトール", "会議費", "課税仕入"),

    # 消耗品費
    ("文具", "消耗品費", "課税仕入"),
    ("コピー", "消耗品費", "課税仕入"),
    ("印刷", "消耗品費", "課税仕入"),
    ("事務用品", "消耗品費", "課税仕入"),
    ("Amazon", "消耗品費", "課税仕入"),
    ("ヨドバシ", "消耗品費", "課税仕入"),
    ("ビックカメラ", "消耗品費", "課税仕入"),
    ("100円", "消耗品費", "課税仕入"),
    ("ダイソー", "消耗品費", "課税仕入"),

    # 通信費
    ("通信", "通信費", "課税仕入"),
    ("電話", "通信費", "課税仕入"),
    ("インターネット", "通信費", "課税仕入"),
    ("プロバイダ", "通信費", "課税仕入"),
    ("ドコモ", "通信費", "課税仕入"),
    ("au", "通信費", "課税仕入"),
    ("ソフトバンク", "通信費", "課税仕入"),
    ("AWS", "通信費", "課税仕入"),
    ("サーバ", "通信費", "課税仕入"),

    # 広告宣伝費
    ("広告", "広告宣伝費", "課税仕入"),
    ("宣伝", "広告宣伝費", "課税仕入"),
    ("Google Ads", "広告宣伝費", "課税仕入"),
    ("Facebook", "広告宣伝費", "課税仕入"),
    ("チラシ", "広告宣伝費", "課税仕入"),

    # 外注費
    ("外注", "外注費", "課税仕入"),
    ("制作", "外注費", "課税仕入"),
    ("開発", "外注費", "課税仕入"),
    ("デザイン", "外注費", "課税仕入"),
    ("業務委託", "外注費", "課税仕入"),
    ("ランサーズ", "外注費", "課税仕入"),
    ("クラウドワークス", "外注費", "課税仕入"),

    # 交際費
    ("接待", "交際費", "課税仕入"),
    ("懇親", "交際費", "課税仕入"),
    ("贈答", "交際費", "課税仕入"),
    ("お中元", "交際費", "課税仕入"),
    ("お歳暮", "交際費", "課税仕入"),
    ("居酒屋", "交際費", "課税仕入"),

    # 地代家賃
    ("家賃", "地代家賃", "非課税仕入"),
    ("賃料", "地代家賃", "非課税仕入"),
    ("オフィス", "地代家賃", "課税仕入"),
    ("コワーキング", "地代家賃", "課税仕入"),
    ("レンタルオフィス", "地代家賃", "課税仕入"),

    # 水道光熱費
    ("電気", "水道光熱費", "課税仕入"),
    ("ガス", "水道光熱費", "課税仕入"),
    ("水道", "水道光熱費", "課税仕入"),
    ("東京電力", "水道光熱費", "課税仕入"),
    ("東京ガス", "水道光熱費", "課税仕入"),

    # 新聞図書費
    ("書籍", "新聞図書費", "課税仕入"),
    ("本", "新聞図書費", "課税仕入"),
    ("新聞", "新聞図書費", "課税仕入"),
    ("雑誌", "新聞図書費", "課税仕入"),
    ("Kindle", "新聞図書費", "課税仕入"),

    # 研修費
    ("研修", "研修費", "課税仕入"),
    ("セミナー", "研修費", "課税仕入"),
    ("講座", "研修費", "課税仕入"),
    ("Udemy", "研修費", "課税仕入"),
]

# Payment method to credit account mapping
PAYMENT_METHOD_ACCOUNTS = {
    "クレジットカード": "未払金",
    "現金": "現金",
    "銀行振込": "普通預金",
    "普通預金": "普通預金",
}


class JournalGenerator:
    """Generate journal entries from extracted data."""

    def __init__(self, db: Optional[Session] = None):
        """Initialize generator with optional database session for custom mappings."""
        self.db = db
        self._load_mappings()

    def _load_mappings(self) -> None:
        """Load account mappings from database or use defaults."""
        self.mappings = []

        # Load from database if available
        if self.db:
            try:
                db_mappings = (
                    self.db.query(AccountMapping)
                    .order_by(AccountMapping.priority.desc())
                    .all()
                )
                for m in db_mappings:
                    self.mappings.append((m.keyword, m.account_name, m.tax_category))
            except Exception as e:
                logger.warning(f"Failed to load mappings from DB: {e}")

        # Add default mappings
        self.mappings.extend(DEFAULT_MAPPINGS)

    def generate(
        self,
        vendor_name: Optional[str],
        description: Optional[str],
        ocr_text: Optional[str],
        payment_method: str = "クレジットカード"
    ) -> JournalSuggestion:
        """Generate journal entry suggestion.

        Args:
            vendor_name: Vendor/store name
            description: Item description
            ocr_text: Full OCR text for additional context
            payment_method: Payment method used

        Returns:
            JournalSuggestion with debit/credit accounts
        """
        # Build search text
        search_text = " ".join(filter(None, [vendor_name, description, ocr_text]))
        search_text = search_text.lower() if search_text else ""

        # Find matching account
        debit_account = "雑費"  # Default
        tax_category = "課税仕入"
        confidence = 0.3  # Low confidence for default

        for keyword, account, tax_cat in self.mappings:
            if keyword.lower() in search_text:
                debit_account = account
                tax_category = tax_cat
                confidence = 0.8  # Higher confidence for keyword match
                logger.info(f"Matched keyword '{keyword}' -> {account}")
                break

        # Get credit account based on payment method
        credit_account = PAYMENT_METHOD_ACCOUNTS.get(
            payment_method, "未払金"
        )

        return JournalSuggestion(
            debit_account=debit_account,
            credit_account=credit_account,
            tax_category=tax_category,
            confidence=confidence
        )

    def get_available_accounts(self) -> dict:
        """Get list of available accounts for UI."""
        return {
            "debit_accounts": [
                "旅費交通費",
                "会議費",
                "消耗品費",
                "通信費",
                "広告宣伝費",
                "外注費",
                "交際費",
                "地代家賃",
                "水道光熱費",
                "新聞図書費",
                "研修費",
                "支払手数料",
                "雑費",
            ],
            "credit_accounts": [
                "未払金",
                "普通預金",
                "現金",
            ],
            "tax_categories": [
                "課税仕入",
                "非課税仕入",
                "不課税",
                "対象外",
            ],
            "payment_methods": [
                "クレジットカード",
                "現金",
                "銀行振込",
            ],
        }


def init_default_mappings(db: Session) -> None:
    """Initialize database with default account mappings."""
    # Check if mappings already exist
    existing = db.query(AccountMapping).first()
    if existing:
        return

    for keyword, account, tax_cat in DEFAULT_MAPPINGS:
        mapping = AccountMapping(
            keyword=keyword,
            account_name=account,
            tax_category=tax_cat
        )
        db.add(mapping)

    try:
        db.commit()
        logger.info("Initialized default account mappings")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize mappings: {e}")
