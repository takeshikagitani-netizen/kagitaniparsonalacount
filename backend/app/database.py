"""
Firestore データベース接続モジュール
"""

import os
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore, auth


@lru_cache()
def get_firebase_app():
    """
    Firebase Admin SDKの初期化
    シングルトンパターンで一度だけ初期化
    """
    # 既に初期化済みの場合はそのアプリを返す
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # 認証情報のパスを取得
    # 環境変数 GOOGLE_APPLICATION_CREDENTIALS にサービスアカウントキーのパスを設定
    cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    if cred_path and os.path.exists(cred_path):
        # サービスアカウントキーファイルを使用
        cred = credentials.Certificate(cred_path)
        return firebase_admin.initialize_app(cred)
    else:
        # デフォルト認証情報を使用（Cloud Run等で実行時）
        # または開発環境用のデフォルト設定
        try:
            return firebase_admin.initialize_app()
        except ValueError:
            # 既に初期化されている場合
            return firebase_admin.get_app()


def get_firestore_client():
    """
    Firestoreクライアントを取得
    """
    get_firebase_app()
    return firestore.client()


def get_auth_client():
    """
    Firebase Authクライアントを取得
    """
    get_firebase_app()
    return auth


# Firestoreコレクション名
COLLECTION_USERS = "users"
COLLECTION_JOURNALS = "journals"
COLLECTION_RECEIPTS = "receipts"
