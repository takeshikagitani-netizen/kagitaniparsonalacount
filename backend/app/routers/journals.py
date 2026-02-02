"""Journal entry management endpoints."""
import csv
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import JournalEntry
from ..schemas import JournalEntryResponse, JournalEntryUpdate
from ..services.journal_generator import JournalGenerator

router = APIRouter(prefix="/journals", tags=["journals"])


@router.get("/", response_model=List[JournalEntryResponse])
async def list_journal_entries(
    skip: int = 0,
    limit: int = 100,
    confirmed_only: bool = False,
    db: Session = Depends(get_db),
):
    """List all journal entries."""
    query = db.query(JournalEntry)

    if confirmed_only:
        query = query.filter(JournalEntry.is_confirmed == 1)

    entries = (
        query.order_by(JournalEntry.transaction_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return entries


@router.get("/accounts")
async def get_account_options():
    """Get available account options for dropdowns."""
    generator = JournalGenerator()
    return generator.get_available_accounts()


@router.get("/export/csv")
async def export_csv(
    confirmed_only: bool = False,
    db: Session = Depends(get_db),
):
    """Export journal entries as CSV.

    CSV format is generic and can be imported to various accounting software:
    - freee
    - Money Forward
    - Yayoi (弥生)

    Columns:
    - 取引日
    - 借方科目
    - 借方金額
    - 貸方科目
    - 貸方金額
    - 摘要
    - 取引先
    - 税区分
    - 支払方法
    """
    query = db.query(JournalEntry)

    if confirmed_only:
        query = query.filter(JournalEntry.is_confirmed == 1)

    entries = query.order_by(JournalEntry.transaction_date.asc()).all()

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "取引日",
        "借方科目",
        "借方金額",
        "貸方科目",
        "貸方金額",
        "摘要",
        "取引先",
        "税区分",
        "支払方法",
    ])

    # Data rows
    for entry in entries:
        writer.writerow([
            entry.transaction_date,
            entry.debit_account,
            int(entry.amount) if entry.amount else 0,
            entry.credit_account,
            int(entry.amount) if entry.amount else 0,
            entry.description or "",
            entry.vendor_name or "",
            entry.tax_category or "",
            entry.payment_method or "",
        ])

    output.seek(0)

    # Return as downloadable file
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=journal_entries.csv"
        }
    )


@router.get("/{journal_id}", response_model=JournalEntryResponse)
async def get_journal_entry(
    journal_id: int,
    db: Session = Depends(get_db),
):
    """Get a specific journal entry by ID."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry


@router.put("/{journal_id}", response_model=JournalEntryResponse)
async def update_journal_entry(
    journal_id: int,
    update_data: JournalEntryUpdate,
    db: Session = Depends(get_db),
):
    """Update a journal entry."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{journal_id}/confirm", response_model=JournalEntryResponse)
async def confirm_journal_entry(
    journal_id: int,
    db: Session = Depends(get_db),
):
    """Confirm a journal entry (mark as verified)."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    entry.is_confirmed = 1
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{journal_id}")
async def delete_journal_entry(
    journal_id: int,
    db: Session = Depends(get_db),
):
    """Delete a journal entry."""
    entry = db.query(JournalEntry).filter(JournalEntry.id == journal_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    db.delete(entry)
    db.commit()
    return {"message": "Journal entry deleted successfully"}
