"""OCR service for extracting text from images.

This module is designed to be easily swappable with different OCR backends.
Currently supports:
- Tesseract (default, free)
- Stub mode (for testing without OCR)

Future support planned:
- Google Cloud Vision
- AWS Textract
- Azure Computer Vision
"""
from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


class OCRBackend(ABC):
    """Abstract base class for OCR backends."""

    @abstractmethod
    def extract_text(self, image_path: str) -> str:
        """Extract text from an image file."""
        pass


class TesseractBackend(OCRBackend):
    """Tesseract OCR backend."""

    def __init__(self, language: str = "jpn+eng"):
        self.language = language
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}")
            return False

    def extract_text(self, image_path: str) -> str:
        """Extract text using Tesseract."""
        if not self._tesseract_available:
            logger.warning("Tesseract not available, returning empty text")
            return ""

        try:
            import pytesseract
            image = Image.open(image_path)

            # Pre-process image for better OCR
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Extract text
            text = pytesseract.image_to_string(
                image,
                lang=self.language,
                config="--psm 6"  # Assume uniform block of text
            )
            return text.strip()

        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""


class StubBackend(OCRBackend):
    """Stub backend for testing without actual OCR."""

    def __init__(self):
        self.stub_texts = {
            "receipt": """
            株式会社テストストア
            東京都渋谷区1-2-3

            2024年1月15日

            コーヒー豆 1kg      ¥2,000
            フィルター         ¥500
            ----------------------
            小計              ¥2,500
            消費税(10%)         ¥250
            ----------------------
            合計              ¥2,750

            お支払い: クレジットカード
            """,
            "invoice": """
            請求書

            発行日: 2024年1月20日

            株式会社サンプル 御中

            件名: ウェブサイト制作費用

            金額: ¥550,000 (税込)
            内訳:
              デザイン費    ¥200,000
              開発費       ¥300,000
              消費税(10%)   ¥50,000

            振込先: みずほ銀行 渋谷支店
            """
        }

    def extract_text(self, image_path: str) -> str:
        """Return stub text for testing."""
        filename = Path(image_path).name.lower()
        if "invoice" in filename or "請求" in filename:
            return self.stub_texts["invoice"]
        return self.stub_texts["receipt"]


class OCRService:
    """Main OCR service with pluggable backends."""

    def __init__(self, backend: str = "tesseract", language: str = "jpn+eng"):
        """Initialize OCR service with specified backend.

        Args:
            backend: OCR backend to use ("tesseract" or "stub")
            language: Language codes for OCR (e.g., "jpn+eng")
        """
        self.backend = self._create_backend(backend, language)
        self.backend_name = backend

    def _create_backend(self, backend: str, language: str) -> OCRBackend:
        """Create OCR backend instance."""
        if backend == "tesseract":
            return TesseractBackend(language)
        elif backend == "stub":
            return StubBackend()
        else:
            logger.warning(f"Unknown backend '{backend}', falling back to stub")
            return StubBackend()

    def extract_text(self, image_path: str) -> str:
        """Extract text from image.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text string
        """
        logger.info(f"Extracting text from {image_path} using {self.backend_name}")
        return self.backend.extract_text(image_path)

    def is_available(self) -> bool:
        """Check if the OCR backend is available."""
        if isinstance(self.backend, TesseractBackend):
            return self.backend._tesseract_available
        return True  # Stub is always available
