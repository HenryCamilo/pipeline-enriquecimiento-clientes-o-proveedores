"""
PDF text extraction with page-level granularity.
Improved for factura/invoice documents:
- pdfplumber first
- PyPDF fallback if embedded text is weak
- selective OCR using page scoring
- keeps same public API used by the rest of the project
"""
from __future__ import annotations

import logging

import pdfplumber

from src.extraction.ocr_reader import ocr_pages
from src.extraction.text_cleaner import clean_text
from src.extraction.page_scorer import score_page, rank_pages, find_pages_needing_ocr

logger = logging.getLogger("pdf_reader")

MIN_TEXT_LENGTH = 80
MIN_PAGE_TEXT_LEN = 30


def _extract_pages_with_pdfplumber(path: str) -> list[str]:
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
    except Exception as e:
        logger.warning("pdfplumber falló en %s: %s", path, e)
    return pages


def _extract_pages_with_pypdf(path: str, expected_pages: int | None = None) -> list[str]:
    try:
        from pypdf import PdfReader
    except Exception:
        return []

    try:
        reader = PdfReader(path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        if expected_pages is not None and expected_pages and len(pages) < expected_pages:
            pages.extend([""] * (expected_pages - len(pages)))
        return pages
    except Exception as e:
        logger.warning("pypdf falló en %s: %s", path, e)
        return []


def _merge_page_texts(primary: list[str], secondary: list[str]) -> list[str]:
    if not primary:
        return secondary
    if not secondary:
        return primary

    max_len = max(len(primary), len(secondary))
    merged = []
    for i in range(max_len):
        a = primary[i] if i < len(primary) else ""
        b = secondary[i] if i < len(secondary) else ""
        merged.append(b if len(b.strip()) > len(a.strip()) else a)
    return merged


def extract_pages_text(path: str) -> list[str]:
    """
    Page-level embedded text extraction with fallback.
    First tries pdfplumber, then supplements with pypdf when useful.
    """
    pages_plumber = _extract_pages_with_pdfplumber(path)
    pages_pypdf = _extract_pages_with_pypdf(path, expected_pages=len(pages_plumber) or None)

    if not pages_plumber and pages_pypdf:
        return pages_pypdf

    return _merge_page_texts(pages_plumber, pages_pypdf)


def _choose_pages_for_ocr(pages_text: list[str], mode: str) -> list[int]:
    total_pages = len(pages_text)
    if total_pages == 0:
        return []

    sparse_pages = find_pages_needing_ocr(pages_text, min_text_len=40)
    useful_ranked = rank_pages(pages_text, threshold=1)

    # Si hay texto útil, OCR solo páginas escasas pero con señales de utilidad.
    if sparse_pages:
        scored_sparse = [(i, score_page(pages_text[i])) for i in sparse_pages]
        worth_ocr = [i for i, s in scored_sparse if s >= 1]

        # si ninguna sparse tiene score, al menos toma primeras útiles o la primera página
        if not worth_ocr:
            worth_ocr = useful_ranked[:3] if useful_ranked else [0]

        if mode == "fast":
            return []
        if mode == "balanced":
            return worth_ocr[:3]
        return worth_ocr

    # Si no hay sparse pages, no hace falta OCR
    return []


def extract_text_smart(path: str, mode: str = "balanced") -> tuple[str, dict]:
    """
    Returns (full_text, metadata).

    metadata:
    - pages_count
    - pages_with_text
    - ocr_page_indices
    - method
    """
    pages_text = extract_pages_text(path)
    total_pages = len(pages_text)

    meta = {
        "pages_count": total_pages,
        "pages_with_text": 0,
        "ocr_page_indices": [],
        "method": "embedded",
    }

    pages_with_text = [i for i, t in enumerate(pages_text) if len((t or "").strip()) >= MIN_PAGE_TEXT_LEN]
    meta["pages_with_text"] = len(pages_with_text)

    combined = "\n".join(pages_text).strip()

    # Caso 1: ya hay texto suficiente
    if combined and len(combined) >= MIN_TEXT_LENGTH:
        if mode == "fast":
            return clean_text(combined), meta

        pages_for_ocr = _choose_pages_for_ocr(pages_text, mode=mode)
        if not pages_for_ocr:
            return clean_text(combined), meta

        ocr_results = ocr_pages(path, pages_for_ocr)
        if ocr_results:
            meta["ocr_page_indices"] = list(ocr_results.keys())
            meta["method"] = "embedded+ocr_selective"

            for idx, ocr_text in ocr_results.items():
                if idx < len(pages_text) and len(ocr_text.strip()) > len((pages_text[idx] or "").strip()):
                    pages_text[idx] = ocr_text

            combined = "\n".join(pages_text).strip()

        return clean_text(combined), meta

    # Caso 2: texto embebido insuficiente
    if mode == "fast":
        return "", meta

    useful_ranked = rank_pages(pages_text, threshold=1)

    if useful_ranked:
        pages_for_ocr = useful_ranked[:3] if mode == "balanced" else useful_ranked
        meta["method"] = "ocr_useful_pages"
    else:
        pages_for_ocr = list(range(total_pages))
        if mode == "balanced":
            pages_for_ocr = pages_for_ocr[:5]
        meta["method"] = "ocr_full"

    ocr_results = ocr_pages(path, pages_for_ocr)
    meta["ocr_page_indices"] = list(ocr_results.keys())

    for idx, ocr_text in ocr_results.items():
        if idx < len(pages_text):
            pages_text[idx] = ocr_text

    combined = "\n".join(pages_text).strip()
    return clean_text(combined), meta


def extract_text_from_pdf(path: str) -> str:
    text, _ = extract_text_smart(path, mode="balanced")
    return text