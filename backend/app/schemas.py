"""Pydantic schemas for request/response validation."""
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


# Receipt schemas
class ReceiptBase(BaseModel):
    """Base receipt schema."""
    extracted_date: Optional[str] = None
    amount_total: Optional[float] = None
    amount_without_tax: Optional[float] = None
    tax_amount: Optional[float] = None
    vendor_name: Optional[str] = None
    description: Optional[str] = None


class ReceiptCreate(ReceiptBase):
    """Schema for creating a receipt (internal use)."""
    original_filename: str
    stored_filename: str
    file_path: str
    ocr_text: Optional[str] = None


class ReceiptResponse(ReceiptBase):
    """Schema for receipt response."""
    id: int
    original_filename: str
    ocr_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Journal Entry schemas
class JournalEntryBase(BaseModel):
    """Base journal entry schema."""
    transaction_date: str
    debit_account: str
    credit_account: str
    amount: float
    tax_category: Optional[str] = None
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    payment_method: str = "クレジットカード"


class JournalEntryCreate(JournalEntryBase):
    """Schema for creating a journal entry."""
    receipt_id: int


class JournalEntryUpdate(BaseModel):
    """Schema for updating a journal entry."""
    transaction_date: Optional[str] = None
    debit_account: Optional[str] = None
    credit_account: Optional[str] = None
    amount: Optional[float] = None
    tax_category: Optional[str] = None
    description: Optional[str] = None
    vendor_name: Optional[str] = None
    payment_method: Optional[str] = None
    is_confirmed: Optional[int] = None


class JournalEntryResponse(JournalEntryBase):
    """Schema for journal entry response."""
    id: int
    receipt_id: int
    is_confirmed: int
    created_at: datetime

    class Config:
        from_attributes = True


# Combined response for upload
class UploadResponse(BaseModel):
    """Response after uploading and processing a receipt."""
    receipt: ReceiptResponse
    journal_entry: JournalEntryResponse
    message: str


# Account mapping schemas
class AccountMappingCreate(BaseModel):
    """Schema for creating account mapping."""
    keyword: str
    account_name: str
    tax_category: str = "課税仕入"
    priority: int = 0


class AccountMappingResponse(AccountMappingCreate):
    """Schema for account mapping response."""
    id: int

    class Config:
        from_attributes = True


# Dummy data request
class DummyDataRequest(BaseModel):
    """Request for creating dummy data."""
    vendor_name: str = "テスト株式会社"
    amount: float = 10000
    date: str = "2024-01-15"
    description: str = "テスト購入"
    payment_method: str = "クレジットカード"
