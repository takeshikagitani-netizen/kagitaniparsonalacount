"""
Firebase サービスモジュール
Firebase Admin SDKを使用した認証・Firestore操作
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError

from app.database import (
    get_firestore_client,
    get_auth_client,
    COLLECTION_USERS,
    COLLECTION_JOURNALS,
)
from app.models import JournalModel, UserModel, JournalStatus
from app.schemas import UserInfo


class FirebaseService:
    """Firebase操作サービスクラス"""

    def __init__(self):
        self.db = get_firestore_client()
        self.auth = get_auth_client()

    # ===========================================
    # 認証関連
    # ===========================================

    def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """
        Firebase IDトークンを検証

        Args:
            id_token: クライアントから送信されたIDトークン

        Returns:
            検証成功時はトークンの情報、失敗時はNone
        """
        try:
            decoded_token = self.auth.verify_id_token(id_token)
            return decoded_token
        except (FirebaseError, ValueError) as e:
            print(f"Token verification failed: {e}")
            return None

    def get_or_create_user(self, uid: str, email: str, display_name: str = None, photo_url: str = None) -> UserInfo:
        """
        ユーザーを取得または作成
        初回ログイン時にFirestoreにユーザー情報を保存

        Args:
            uid: Firebase UID
            email: メールアドレス
            display_name: 表示名
            photo_url: プロフィール画像URL

        Returns:
            UserInfo: ユーザー情報
        """
        user_ref = self.db.collection(COLLECTION_USERS).document(uid)
        user_doc = user_ref.get()

        if user_doc.exists:
            # 既存ユーザー：最終ログイン日時を更新
            user_data = user_doc.to_dict()
            user_ref.update({
                "last_login_at": datetime.utcnow(),
                "display_name": display_name or user_data.get("display_name"),
                "photo_url": photo_url or user_data.get("photo_url"),
            })
            return UserInfo(
                uid=uid,
                email=user_data.get("email", email),
                display_name=display_name or user_data.get("display_name"),
                photo_url=photo_url or user_data.get("photo_url"),
                role=user_data.get("role", "user"),
            )
        else:
            # 新規ユーザー：ユーザー情報を作成
            user_model = UserModel(
                id=uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                role="user",
            )
            user_ref.set(user_model.to_dict())
            return UserInfo(
                uid=uid,
                email=email,
                display_name=display_name,
                photo_url=photo_url,
                role="user",
            )

    # ===========================================
    # 仕訳関連
    # ===========================================

    def create_journal(
        self,
        user_id: str,
        date: str,
        amount: int,
        tax_rate: int,
        debit_account: str,
        credit_account: str,
        description: str,
        receipt_url: str = None,
        receipt_filename: str = None,
        status: str = JournalStatus.PENDING.value,
    ) -> JournalModel:
        """
        新しい仕訳を作成

        Args:
            user_id: ユーザーID
            date: 仕訳日付
            amount: 金額
            tax_rate: 税率
            debit_account: 借方科目
            credit_account: 貸方科目
            description: 摘要
            receipt_url: 領収書画像URL
            receipt_filename: 領収書ファイル名
            status: ステータス

        Returns:
            JournalModel: 作成された仕訳
        """
        # ユニークなIDを生成
        journal_id = str(uuid.uuid4())

        journal = JournalModel(
            id=journal_id,
            user_id=user_id,
            date=date,
            amount=amount,
            tax_rate=tax_rate,
            debit_account=debit_account,
            credit_account=credit_account,
            description=description,
            status=status,
            receipt_url=receipt_url,
            receipt_filename=receipt_filename,
        )

        # Firestoreに保存
        self.db.collection(COLLECTION_JOURNALS).document(journal_id).set(journal.to_dict())

        return journal

    def get_journal(self, journal_id: str, user_id: str) -> Optional[JournalModel]:
        """
        仕訳を取得（ユーザーIDでアクセス制御）

        Args:
            journal_id: 仕訳ID
            user_id: ユーザーID

        Returns:
            JournalModel: 仕訳データ、存在しない場合はNone
        """
        doc = self.db.collection(COLLECTION_JOURNALS).document(journal_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict()

        # ユーザーIDが一致しない場合はアクセス拒否
        if data.get("user_id") != user_id:
            return None

        return JournalModel.from_dict(doc.id, data)

    def get_journals_by_user(self, user_id: str, limit: int = 100) -> List[JournalModel]:
        """
        ユーザーの仕訳一覧を取得

        Args:
            user_id: ユーザーID
            limit: 取得件数上限

        Returns:
            List[JournalModel]: 仕訳リスト
        """
        query = (
            self.db.collection(COLLECTION_JOURNALS)
            .where("user_id", "==", user_id)
            .order_by("created_at", direction="DESCENDING")
            .limit(limit)
        )

        journals = []
        for doc in query.stream():
            journals.append(JournalModel.from_dict(doc.id, doc.to_dict()))

        return journals

    def update_journal(
        self,
        journal_id: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Optional[JournalModel]:
        """
        仕訳を更新

        Args:
            journal_id: 仕訳ID
            user_id: ユーザーID
            updates: 更新データ

        Returns:
            JournalModel: 更新後の仕訳、失敗時はNone
        """
        # 既存の仕訳を取得（アクセス制御含む）
        journal = self.get_journal(journal_id, user_id)
        if not journal:
            return None

        # 更新日時を追加
        updates["updated_at"] = datetime.utcnow()

        # Firestoreを更新
        self.db.collection(COLLECTION_JOURNALS).document(journal_id).update(updates)

        # 更新後のデータを取得して返す
        return self.get_journal(journal_id, user_id)

    def confirm_journal(
        self,
        journal_id: str,
        user_id: str,
        date: str,
        amount: int,
        tax_rate: int,
        debit_account: str,
        credit_account: str,
        description: str,
    ) -> Optional[JournalModel]:
        """
        仕訳を確定

        Args:
            journal_id: 仕訳ID
            user_id: ユーザーID
            その他: 確定時の仕訳データ

        Returns:
            JournalModel: 確定後の仕訳
        """
        updates = {
            "date": date,
            "amount": amount,
            "tax_rate": tax_rate,
            "debit_account": debit_account,
            "credit_account": credit_account,
            "description": description,
            "status": JournalStatus.CONFIRMED.value,
        }

        return self.update_journal(journal_id, user_id, updates)

    def delete_journal(self, journal_id: str, user_id: str) -> bool:
        """
        仕訳を削除

        Args:
            journal_id: 仕訳ID
            user_id: ユーザーID

        Returns:
            bool: 削除成功時True
        """
        # アクセス制御
        journal = self.get_journal(journal_id, user_id)
        if not journal:
            return False

        self.db.collection(COLLECTION_JOURNALS).document(journal_id).delete()
        return True
