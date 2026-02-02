"""
認証関連のルーター
Firebase Authentication IDトークンの検証
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.firebase_service import FirebaseService
from app.schemas import UserInfo, MessageResponse

router = APIRouter()

# Bearer トークン認証スキーム
security = HTTPBearer(auto_error=False)

# Firebase サービスのシングルトン
_firebase_service: Optional[FirebaseService] = None


def get_firebase_service() -> FirebaseService:
    """FirebaseServiceのシングルトンを取得"""
    global _firebase_service
    if _firebase_service is None:
        _firebase_service = FirebaseService()
    return _firebase_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    firebase_service: FirebaseService = Depends(get_firebase_service),
) -> UserInfo:
    """
    現在のユーザーを取得する依存関数
    Authorizationヘッダーからトークンを取得し、Firebaseで検証

    使用例:
        @router.get("/protected")
        async def protected_route(current_user: UserInfo = Depends(get_current_user)):
            return {"user": current_user}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # トークンを検証
    decoded_token = firebase_service.verify_id_token(token)

    if not decoded_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ユーザー情報を取得または作成
    uid = decoded_token.get("uid")
    email = decoded_token.get("email", "")
    display_name = decoded_token.get("name")
    photo_url = decoded_token.get("picture")

    user = firebase_service.get_or_create_user(
        uid=uid,
        email=email,
        display_name=display_name,
        photo_url=photo_url,
    )

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    firebase_service: FirebaseService = Depends(get_firebase_service),
) -> Optional[UserInfo]:
    """
    現在のユーザーを取得（オプション）
    認証がなくてもエラーにならない
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, firebase_service)
    except HTTPException:
        return None


# ===========================================
# 認証エンドポイント
# ===========================================

@router.get("/auth/me", response_model=UserInfo)
async def get_me(current_user: UserInfo = Depends(get_current_user)):
    """
    現在のユーザー情報を取得

    このエンドポイントを呼び出すことで:
    1. トークンの有効性を確認
    2. ユーザー情報を取得
    3. 必要に応じてFirestoreにユーザーを登録
    """
    return current_user


@router.post("/auth/verify", response_model=MessageResponse)
async def verify_token(current_user: UserInfo = Depends(get_current_user)):
    """
    トークンの有効性を確認

    トークンが有効な場合は成功メッセージを返す
    無効な場合は401エラー
    """
    return MessageResponse(
        message=f"トークンは有効です。ユーザー: {current_user.email}",
        status="ok"
    )
