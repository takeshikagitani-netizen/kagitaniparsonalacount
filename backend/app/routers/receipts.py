"""Receipt upload and processing endpoints."""
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Receipt, JournalEntry
from ..schemas import ReceiptResponse, UploadResponse, DummyDataRequest
from ..services import OCRService, DataExtractor, JournalGenerator

router = APIRouter(prefix="/receipts", tags=["receipts"])
settings = get_settings()


def get_ocr_service() -> OCRService:
    """Get OCR service instance."""
    return OCRService(language=settings.ocr_language)


@router.post("/upload", response_model=UploadResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    payment_method: str = Form("クレジットカード"),
    db: Session = Depends(get_db),
    ocr_service: OCRService = Depends(get_ocr_service),
):
    """Upload a receipt/invoice image and process it.

    1. Save the image file
    2. Extract text using OCR
    3. Parse extracted data (date, amount, vendor, etc.)
    4. Generate journal entry suggestion
    5. Save to database

    Returns the receipt data and suggested journal entry.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Use JPEG, PNG, GIF, WebP, or PDF."
        )

    # Check file size
    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB."
        )

    # Generate unique filename
    ext = Path(file.filename).suffix or ".jpg"
    stored_filename = f"{uuid.uuid4()}{ext}"
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    file_path = storage_path / stored_filename

    # Save file
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        # OCR extraction
        ocr_text = ocr_service.extract_text(str(file_path))

        # Data extraction
        extractor = DataExtractor()
        extracted = extractor.extract(ocr_text)

        # Create receipt record
        receipt = Receipt(
            original_filename=file.filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
            ocr_text=ocr_text,
            extracted_date=extracted.date,
            amount_total=extracted.amount_total,
            amount_without_tax=extracted.amount_without_tax,
            tax_amount=extracted.tax_amount,
            vendor_name=extracted.vendor_name,
            description=extracted.description,
        )
        db.add(receipt)
        db.flush()  # Get receipt.id

        # Generate journal entry
        generator = JournalGenerator(db)
        suggestion = generator.generate(
            vendor_name=extracted.vendor_name,
            description=extracted.description,
            ocr_text=ocr_text,
            payment_method=payment_method
        )

        # Create journal entry record
        journal_entry = JournalEntry(
            receipt_id=receipt.id,
            transaction_date=extracted.date or datetime.now().strftime("%Y-%m-%d"),
            debit_account=suggestion.debit_account,
            credit_account=suggestion.credit_account,
            amount=extracted.amount_total or 0,
            tax_category=suggestion.tax_category,
            description=extracted.description,
            vendor_name=extracted.vendor_name,
            payment_method=payment_method,
        )
        db.add(journal_entry)
        db.commit()
        db.refresh(receipt)
        db.refresh(journal_entry)

        return UploadResponse(
            receipt=ReceiptResponse.model_validate(receipt),
            journal_entry=journal_entry,
            message="Receipt processed successfully"
        )

    except Exception as e:
        db.rollback()
        # Clean up file on error
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dummy", response_model=UploadResponse)
async def create_dummy_receipt(
    data: DummyDataRequest,
    db: Session = Depends(get_db),
):
    """Create a dummy receipt for testing without actual image upload.

    Useful for testing the workflow without OCR/images.
    """
    # Create receipt record
    receipt = Receipt(
        original_filename="dummy_receipt.jpg",
        stored_filename="dummy.jpg",
        file_path="dummy",
        ocr_text=f"{data.vendor_name}\n{data.date}\n{data.description}\n合計: ¥{data.amount:,.0f}",
        extracted_date=data.date,
        amount_total=data.amount,
        amount_without_tax=round(data.amount * 100 / 110, 0),
        tax_amount=round(data.amount * 10 / 110, 0),
        vendor_name=data.vendor_name,
        description=data.description,
    )
    db.add(receipt)
    db.flush()

    # Generate journal entry
    generator = JournalGenerator(db)
    suggestion = generator.generate(
        vendor_name=data.vendor_name,
        description=data.description,
        ocr_text=receipt.ocr_text,
        payment_method=data.payment_method
    )

    journal_entry = JournalEntry(
        receipt_id=receipt.id,
        transaction_date=data.date,
        debit_account=suggestion.debit_account,
        credit_account=suggestion.credit_account,
        amount=data.amount,
        tax_category=suggestion.tax_category,
        description=data.description,
        vendor_name=data.vendor_name,
        payment_method=data.payment_method,
    )
    db.add(journal_entry)
    db.commit()
    db.refresh(receipt)
    db.refresh(journal_entry)

    return UploadResponse(
        receipt=ReceiptResponse.model_validate(receipt),
        journal_entry=journal_entry,
        message="Dummy receipt created successfully"
    )


@router.get("/", response_model=List[ReceiptResponse])
async def list_receipts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all receipts."""
    receipts = (
        db.query(Receipt)
        .order_by(Receipt.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return receipts


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific receipt by ID."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.delete("/{receipt_id}")
async def delete_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
):
    """Delete a receipt and its associated journal entry."""
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Delete file if exists
    if receipt.file_path and receipt.file_path != "dummy":
        file_path = Path(receipt.file_path)
        if file_path.exists():
            file_path.unlink()

    # Delete journal entry (cascade should handle this, but be explicit)
    db.query(JournalEntry).filter(JournalEntry.receipt_id == receipt_id).delete()

    db.delete(receipt)
    db.commit()

    return {"message": "Receipt deleted successfully"}
