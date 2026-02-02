"""SQLAlchemy models for the application."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Receipt(Base):
    """Receipt/Invoice image and extracted data."""

    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)

    # File info
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)

    # Extracted data
    ocr_text = Column(Text, nullable=True)
    extracted_date = Column(String(50), nullable=True)  # Store as string for flexibility
    amount_total = Column(Float, nullable=True)  # 税込金額
    amount_without_tax = Column(Float, nullable=True)  # 税抜金額
    tax_amount = Column(Float, nullable=True)  # 消費税額
    vendor_name = Column(String(255), nullable=True)  # 取引先
    description = Column(String(500), nullable=True)  # 品目/摘要

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    journal_entry = relationship("JournalEntry", back_populates="receipt", uselist=False)


class JournalEntry(Base):
    """Generated journal entry (仕訳)."""

    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)

    # Journal entry data
    transaction_date = Column(String(50), nullable=False)  # 取引日
    debit_account = Column(String(100), nullable=False)  # 借方科目
    credit_account = Column(String(100), nullable=False)  # 貸方科目
    amount = Column(Float, nullable=False)  # 金額
    tax_category = Column(String(50), nullable=True)  # 税区分
    description = Column(String(500), nullable=True)  # 摘要
    vendor_name = Column(String(255), nullable=True)  # 取引先

    # Payment method used
    payment_method = Column(String(50), default="クレジットカード")  # 支払手段

    # Status
    is_confirmed = Column(Integer, default=0)  # 0: 未確定, 1: 確定済み

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    receipt = relationship("Receipt", back_populates="journal_entry")


class AccountMapping(Base):
    """Keyword to account mapping for rule-based classification."""

    __tablename__ = "account_mappings"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String(100), nullable=False, index=True)
    account_name = Column(String(100), nullable=False)
    tax_category = Column(String(50), default="課税仕入")
    priority = Column(Integer, default=0)  # Higher priority = checked first
