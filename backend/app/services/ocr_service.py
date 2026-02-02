"""
OCR サービスモジュール
領収書画像から情報を抽出

注意: 本番環境では Google Cloud Vision API や Azure Computer Vision などの
実際のOCRサービスを使用することを推奨します。
このモジュールはMVP用のシンプルな実装です。
"""

import re
from datetime import date, datetime
from typing import Dict, Any, Optional
import random


class OCRService:
    """
    OCR処理サービス

    MVP版では実際のOCR処理は行わず、
    サンプルデータを返すシンプルな実装となっています。

    本番環境では以下のいずれかを使用することを推奨:
    - Google Cloud Vision API
    - Azure Computer Vision
    - AWS Textract
    - Tesseract OCR
    """

    # 科目推定用のキーワードマッピング
    ACCOUNT_KEYWORDS = {
        "消耗品費": ["文房具", "事務用品", "コピー", "プリンタ", "電池", "USB", "ケーブル"],
        "旅費交通費": ["タクシー", "電車", "バス", "新幹線", "航空", "駐車場", "ガソリン", "ETC"],
        "交際費": ["接待", "贈答", "お歳暮", "お中元", "手土産"],
        "会議費": ["会議", "打ち合わせ", "カフェ", "コーヒー", "喫茶"],
        "通信費": ["電話", "携帯", "インターネット", "通信", "郵便", "宅配"],
        "水道光熱費": ["電気", "ガス", "水道"],
        "広告宣伝費": ["広告", "チラシ", "看板", "WEB広告", "SNS"],
        "福利厚生費": ["健康診断", "社員旅行", "慶弔", "制服"],
        "仕入高": ["仕入", "商品", "材料", "原材料"],
        "外注費": ["外注", "業務委託", "デザイン", "開発"],
    }

    def __init__(self):
        pass

    def extract_receipt_data(
        self,
        file_content: bytes,
        filename: str,
        content_type: str
    ) -> Dict[str, Any]:
        """
        領収書画像からデータを抽出

        Args:
            file_content: ファイルの内容（バイナリ）
            filename: ファイル名
            content_type: MIMEタイプ

        Returns:
            抽出されたデータ
        """
        # MVP版: サンプルデータを返す
        # 本番では実際のOCR処理を行う

        # ファイル名から日付を推定（例: receipt_20240115.jpg）
        extracted_date = self._extract_date_from_filename(filename)
        if not extracted_date:
            extracted_date = date.today().isoformat()

        # サンプル金額を生成（実際はOCRで抽出）
        sample_amounts = [980, 1280, 1980, 2500, 3300, 5500, 8800, 11000, 15000]
        amount = random.choice(sample_amounts)

        # 税率を推定（デフォルト10%）
        tax_rate = 10

        # 科目を推定（ファイル名からキーワードを探す）
        debit_account = self._estimate_account(filename.lower())

        # 摘要を生成
        description = self._generate_description(filename)

        return {
            "date": extracted_date,
            "amount": amount,
            "tax_rate": tax_rate,
            "debit_account": debit_account,
            "credit_account": "現金",
            "description": description,
        }

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """
        ファイル名から日付を抽出

        対応フォーマット:
        - 20240115
        - 2024-01-15
        - 2024_01_15
        """
        # YYYYMMDD形式
        match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if match:
            year, month, day = match.groups()
            try:
                d = date(int(year), int(month), int(day))
                return d.isoformat()
            except ValueError:
                pass

        # YYYY-MM-DD または YYYY_MM_DD 形式
        match = re.search(r'(\d{4})[-_](\d{2})[-_](\d{2})', filename)
        if match:
            year, month, day = match.groups()
            try:
                d = date(int(year), int(month), int(day))
                return d.isoformat()
            except ValueError:
                pass

        return None

    def _estimate_account(self, text: str) -> str:
        """
        テキストから勘定科目を推定
        """
        for account, keywords in self.ACCOUNT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return account

        # デフォルトは消耗品費
        return "消耗品費"

    def _generate_description(self, filename: str) -> str:
        """
        ファイル名から摘要を生成
        """
        # 拡張子を除去
        name = re.sub(r'\.[^.]+$', '', filename)

        # アンダースコアやハイフンをスペースに変換
        name = re.sub(r'[_-]', ' ', name)

        # 数字のみの部分を除去
        name = re.sub(r'\b\d+\b', '', name)

        # 余分なスペースを整理
        name = re.sub(r'\s+', ' ', name).strip()

        if name:
            return f"領収書: {name}"
        else:
            return "領収書"


# シングルトンインスタンス
_ocr_service = None


def get_ocr_service() -> OCRService:
    """OCRサービスのシングルトンインスタンスを取得"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService()
    return _ocr_service
