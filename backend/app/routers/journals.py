"""
仕訳関連のルーター
領収書アップロード、仕訳CRUD操作
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File

from app.routers.auth import get_current_user, get_firebase_service
from app.services.firebase_service import FirebaseService
from app.services.ocr_service import get_ocr_service, OCRService
from app.schemas import (
    UserInfo,
    JournalResponse,
    JournalConfirm,
    UploadResponse,
    MessageResponse,
)
from app.models import JournalStatus

router = APIRouter()


# ===========================================
# アップロード エンドポイント
# ===========================================

@router.post("/upload", response_model=UploadResponse)
async def upload_receipt(
    file: UploadFile = File(...),
    current_user: UserInfo = Depends(get_current_user),
    firebase_service: FirebaseService = Depends(get_firebase_service),
):
    """
    領収書画像をアップロードして仕訳を生成

    1. 画像をアップロード
    2. OCRで情報を抽出（MVP版ではサンプルデータ）
    3. 仮の仕訳エントリを作成（status=pending）
    4. 抽出結果を返す
    """
    # ファイル検証
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ファイル名が必要です"
        )

    # MIMEタイプ検証
    allowed_types = ["image/jpeg", "image/png", "image/gif", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(allowed_types)}"
        )

    # ファイルサイズ検証（10MB上限）
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ファイルサイズが大きすぎます（最大10MB）"
        )

    # OCR処理
    ocr_service = get_ocr_service()
    extracted_data = ocr_service.extract_receipt_data(
        file_content=content,
        filename=file.filename,
        content_type=file.content_type,
    )

    # 仮の仕訳を作成
    journal = firebase_service.create_journal(
        user_id=current_user.uid,
        date=extracted_data["date"],
        amount=extracted_data["amount"],
        tax_rate=extracted_data["tax_rate"],
        debit_account=extracted_data["debit_account"],
        credit_account=extracted_data["credit_account"],
        description=extracted_data["description"],
        receipt_filename=file.filename,
        status=JournalStatus.PENDING.value,
    )

    return UploadResponse(
        journal_id=journal.id,
        date=extracted_data["date"],
        amount=extracted_data["amount"],
        tax_rate=extracted_data["tax_rate"],
        debit_account=extracted_data["debit_account"],
        credit_account=extracted_data["credit_account"],
        description=extracted_data["description"],
    )


# ===========================================
# 仕訳 CRUD エンドポイント
# ===========================================

@router.get("/journals", response_model=List[JournalResponse])
async def list_journals(
    current_user: UserInfo = Depends(get_current_user),
    firebase_service: FirebaseService = Depends(get_firebase_service),
):
    """
    ユーザーの仕訳一覧を取得

    自分の仕訳のみ取得可能（他ユーザーのデータは見えない）
    """
    journals = firebase_service.get_journals_by_user(current_user.uid)

    return [
        JournalResponse(
            id=j.id,
            user_id=j.user_id,
            date=j.date,
            amount=j.amount,
            tax_rate=j.tax_rate,
            debit_account=j.debit_account,
            credit_account=j.credit_account,
            description=j.description,
            status=j.status,
            receipt_url=j.receipt_url,
            receipt_filename=j.receipt_filename,
            created_at=j.created_at,
            updated_at=j.updated_at,
        )
        for j in journals
    ]


@router.get("/journals/{journal_id}", response_model=JournalResponse)
async def get_journal(
    journal_id: str,
    current_user: UserInfo = Depends(get_current_user),
    firebase_service: FirebaseService = Depends(get_firebase_service),
):
    """
    仕訳を取得

    自分の仕訳のみ取得可能
    """
    journal = firebase_service.get_journal(journal_id, current_user.uid)

    if not journal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="仕訳が見つかりません"
        )

    return JournalResponse(
        id=journal.id,
        user_id=journal.user_id,
        date=journal.date,
        amount=journal.amount,
        tax_rate=journal.tax_rate,
        debit_account=journal.debit_account,
        credit_account=journal.credit_account,
        description=journal.description,
        status=journal.status,
        receipt_url=journal.receipt_url,
        receipt_filename=journal.receipt_filename,
        created_at=journal.created_at,
        updated_at=journal.updated_at,
    )


@router.post("/journals/confirm", response_model=JournalResponse)
async def confirm_journal(
    data: JournalConfirm,
    current_user: UserInfo = Depends(get_current_user),
    firebase_service: FirebaseService = Depends(get_firebase_service),
):
    """
    仕訳を確定

    ユーザーが内容を確認・編集して確定する
    ステータスが pending → confirmed に変更される
    """
    journal = firebase_service.confirm_journal(
        journal_id=data.journal_id,
        user_id=current_user.uid,
        date=data.date,
        amount=data.amount,
        tax_rate=data.tax_rate,
        debit_account=data.debit_account,
        credit_account=data.credit_account,
        description=data.description,
    )

    if not journal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="仕訳が見つかりません"
        )

    return JournalResponse(
        id=journal.id,
        user_id=journal.user_id,
        date=journal.date,
        amount=journal.amount,
        tax_rate=journal.tax_rate,
        debit_account=journal.debit_account,
        credit_account=journal.credit_account,
        description=journal.description,
        status=journal.status,
        receipt_url=journal.receipt_url,
        receipt_filename=journal.receipt_filename,
        created_at=journal.created_at,
        updated_at=journal.updated_at,
    )


@router.delete("/journals/{journal_id}", response_model=MessageResponse)
async def delete_journal(
    journal_id: str,
    current_user: UserInfo = Depends(get_current_user),
    firebase_service: FirebaseService = Depends(get_firebase_service),
):
    """
    仕訳を削除

    自分の仕訳のみ削除可能
    """
    success = firebase_service.delete_journal(journal_id, current_user.uid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="仕訳が見つかりません"
        )

    return MessageResponse(message="仕訳を削除しました")
