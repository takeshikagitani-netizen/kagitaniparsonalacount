"""Data extraction service for parsing OCR text.

Extracts structured data from raw OCR text:
- Date
- Amount (total, without tax, tax amount)
- Vendor name
- Description/items
"""
import re
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ExtractedData:
    """Container for extracted receipt/invoice data."""
    date: Optional[str] = None
    amount_total: Optional[float] = None
    amount_without_tax: Optional[float] = None
    tax_amount: Optional[float] = None
    vendor_name: Optional[str] = None
    description: Optional[str] = None


class DataExtractor:
    """Extract structured data from OCR text."""

    # Date patterns (Japanese and common formats)
    DATE_PATTERNS = [
        # 2024年1月15日
        r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",
        # 2024/01/15 or 2024-01-15
        r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})",
        # R6.1.15 (Japanese era - Reiwa)
        r"[Rr令](\d{1,2})[\.年](\d{1,2})[\.月](\d{1,2})",
        # 01/15/2024 (US format)
        r"(\d{1,2})/(\d{1,2})/(\d{4})",
    ]

    # Amount patterns
    AMOUNT_PATTERNS = [
        # 合計 ¥1,234 or 合計: 1,234円
        (r"合計[:\s]*[¥￥]?\s*([\d,]+)", "total"),
        (r"合計[:\s]*([\d,]+)\s*円", "total"),
        # 税込 or 税込金額
        (r"税込[金額]*[:\s]*[¥￥]?\s*([\d,]+)", "total"),
        (r"税込[金額]*[:\s]*([\d,]+)\s*円", "total"),
        # お支払い or 支払金額
        (r"お?支払[い金額]*[:\s]*[¥￥]?\s*([\d,]+)", "total"),
        # 小計 (subtotal without tax)
        (r"小計[:\s]*[¥￥]?\s*([\d,]+)", "subtotal"),
        (r"小計[:\s]*([\d,]+)\s*円", "subtotal"),
        # 税抜
        (r"税抜[金額]*[:\s]*[¥￥]?\s*([\d,]+)", "subtotal"),
        # 消費税
        (r"消費税[:\s]*[¥￥]?\s*([\d,]+)", "tax"),
        (r"消費税[:\s]*([\d,]+)\s*円", "tax"),
        (r"税[額]*[:\s]*[¥￥]?\s*([\d,]+)", "tax"),
        # Generic amount (fallback)
        (r"[¥￥]\s*([\d,]+)", "generic"),
        (r"([\d,]+)\s*円", "generic"),
    ]

    def extract(self, ocr_text: str) -> ExtractedData:
        """Extract structured data from OCR text.

        Args:
            ocr_text: Raw text from OCR

        Returns:
            ExtractedData with parsed values
        """
        data = ExtractedData()

        if not ocr_text:
            return data

        # Extract each field
        data.date = self._extract_date(ocr_text)
        amounts = self._extract_amounts(ocr_text)
        data.amount_total = amounts.get("total")
        data.amount_without_tax = amounts.get("subtotal")
        data.tax_amount = amounts.get("tax")
        data.vendor_name = self._extract_vendor(ocr_text)
        data.description = self._extract_description(ocr_text)

        # Calculate missing amounts if possible
        self._calculate_missing_amounts(data)

        logger.info(f"Extracted data: {data}")
        return data

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from text."""
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3:
                        # Check if it's Japanese era (Reiwa)
                        if pattern.startswith(r"[Rr令]"):
                            year = 2018 + int(groups[0])  # Reiwa started in 2019
                        elif int(groups[0]) > 12:  # Year first
                            year = int(groups[0])
                        else:  # Month first (US format)
                            return f"{groups[2]}-{groups[0]:0>2}-{groups[1]:0>2}"

                        if int(groups[0]) > 12:  # Year-Month-Day format
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:
                            year = 2018 + int(groups[0])  # Assume Reiwa
                            month, day = int(groups[1]), int(groups[2])

                        return f"{year}-{month:02d}-{day:02d}"
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_amounts(self, text: str) -> dict:
        """Extract various amounts from text."""
        amounts = {"total": None, "subtotal": None, "tax": None, "generic": []}

        for pattern, amount_type in self.AMOUNT_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    amount = float(match.replace(",", ""))
                    if amount > 0:
                        if amount_type == "generic":
                            amounts["generic"].append(amount)
                        elif amounts[amount_type] is None:
                            amounts[amount_type] = amount
                except ValueError:
                    continue

        # If no specific total found, use largest generic amount
        if amounts["total"] is None and amounts["generic"]:
            amounts["total"] = max(amounts["generic"])

        return amounts

    def _extract_vendor(self, text: str) -> Optional[str]:
        """Extract vendor/store name from text."""
        lines = text.strip().split("\n")

        # Common patterns for vendor names
        vendor_patterns = [
            r"^(株式会社.+?)(?:\s|$)",
            r"^(.+株式会社)(?:\s|$)",
            r"^(有限会社.+?)(?:\s|$)",
            r"^(.+有限会社)(?:\s|$)",
            r"^(.+店)(?:\s|$)",
            r"^(.+ストア)(?:\s|$)",
        ]

        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if not line or len(line) < 2:
                continue

            for pattern in vendor_patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(1).strip()

            # If first non-empty line looks like a name (no numbers, reasonable length)
            if (
                not re.search(r"\d", line)
                and 2 <= len(line) <= 30
                and not any(kw in line for kw in ["領収", "請求", "日付", "御中"])
            ):
                return line

        return None

    def _extract_description(self, text: str) -> Optional[str]:
        """Extract description/items from text."""
        # Look for item lines (lines with prices)
        items = []
        item_patterns = [
            r"^(.+?)\s+[¥￥]?\s*[\d,]+\s*円?$",
            r"^(.+?)\s+[\d,]+$",
        ]

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip header/footer lines
            skip_keywords = [
                "合計", "小計", "消費税", "税込", "税抜",
                "お支払", "領収", "請求", "日付", "株式会社",
                "有限会社", "電話", "TEL", "住所"
            ]
            if any(kw in line for kw in skip_keywords):
                continue

            for pattern in item_patterns:
                match = re.match(pattern, line)
                if match:
                    item = match.group(1).strip()
                    if 2 <= len(item) <= 50:
                        items.append(item)
                        break

        if items:
            # Return first few items as description
            return ", ".join(items[:3])

        # Look for 件名 or 内容 field
        desc_patterns = [
            r"件名[:\s]*(.+)",
            r"内容[:\s]*(.+)",
            r"品名[:\s]*(.+)",
            r"摘要[:\s]*(.+)",
        ]
        for pattern in desc_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _calculate_missing_amounts(self, data: ExtractedData) -> None:
        """Calculate missing amount fields if possible."""
        # If we have subtotal and tax, calculate total
        if data.amount_total is None and data.amount_without_tax and data.tax_amount:
            data.amount_total = data.amount_without_tax + data.tax_amount

        # If we have total and tax, calculate subtotal
        if data.amount_without_tax is None and data.amount_total and data.tax_amount:
            data.amount_without_tax = data.amount_total - data.tax_amount

        # If we have total and subtotal, calculate tax
        if data.tax_amount is None and data.amount_total and data.amount_without_tax:
            data.tax_amount = data.amount_total - data.amount_without_tax

        # Estimate tax if we only have total (assume 10%)
        if data.tax_amount is None and data.amount_total:
            data.tax_amount = round(data.amount_total * 10 / 110, 0)
            data.amount_without_tax = data.amount_total - data.tax_amount
