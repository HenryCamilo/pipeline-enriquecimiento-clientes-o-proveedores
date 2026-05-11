from __future__ import annotations

import re
from functools import lru_cache

import pytesseract
from pdf2image import convert_from_path
from paddleocr import PaddleOCR


@lru_cache(maxsize=1)
def get_paddle_ocr(lang: str = "es") -> PaddleOCR:
    """
    Instancia única de PaddleOCR para evitar recargar el modelo en cada página.
    """
    return PaddleOCR(
        use_angle_cls=True,
        lang=lang,
        show_log=False,
    )


def clean_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def image_to_text_with_paddle(image, lang: str = "es") -> str:
    """
    Ejecuta OCR sobre una imagen PIL usando PaddleOCR y devuelve texto plano.
    """
    ocr = get_paddle_ocr(lang=lang)

    import numpy as np
    img_np = np.array(image)

    result = ocr.ocr(img_np, cls=True)

    lines = []
    if result:
        for block in result:
            if not block:
                continue
            for item in block:
                if not item or len(item) < 2:
                    continue
                text = item[1][0]
                if text:
                    lines.append(str(text).strip())

    return clean_ocr_text("\n".join(lines))


def image_to_text_with_tesseract(image, lang: str = "spa") -> str:
    """
    OCR alternativo con Tesseract.
    """
    text = pytesseract.image_to_string(image, lang=lang)
    return clean_ocr_text(text)


def score_ocr_text(text: str) -> int:
    """
    Puntúa qué tan útil parece un texto OCR para tus documentos contables.
    No mide perfección lingüística; mide utilidad para extracción.
    """
    if not text:
        return -999

    upper = text.upper()
    score = 0

    # Longitud útil
    score += min(len(text) // 80, 20)

    # Señales fuertes de documentos relevantes
    strong_keywords = [
        "NIT", "FACTURA", "INVOICE", "CUFE", "CUDE",
        "REGISTRO UNICO TRIBUTARIO", "REGISTRO ÚNICO TRIBUTARIO",
        "DIRECCION", "DIRECCIÓN", "CIUDAD", "MUNICIPIO",
        "RESPONSABILIDADES", "ADQUIRIENTE", "CLIENTE",
        "RAZON SOCIAL", "RAZÓN SOCIAL", "TELEFONO", "TELÉFONO",
        "EMAIL", "CORREO", "FACTURADOR ELECTRONICO", "FACTURADOR ELECTRÓNICO",
    ]
    for kw in strong_keywords:
        if kw in upper:
            score += 4

    # Emails
    emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text, re.IGNORECASE)
    score += len(emails) * 3

    # Números tipo NIT / teléfono / códigos
    numeric_hits = re.findall(r"\b\d{3,}\b", text)
    score += min(len(numeric_hits), 10)

    # Penalización por demasiado ruido raro
    weird_chars = re.findall(r"[^\w\s\.\,\-\:\#\@\(\)\/áéíóúÁÉÍÓÚñÑ]", text)
    score -= min(len(weird_chars), 15)

    # Penalizar texto excesivamente corto
    if len(text.strip()) < 30:
        score -= 10

    return score


def choose_best_ocr_text(paddle_text: str, tesseract_text: str) -> str:
    """
    Selecciona el mejor OCR entre Paddle y Tesseract.
    """
    paddle_score = score_ocr_text(paddle_text)
    tesseract_score = score_ocr_text(tesseract_text)

    if paddle_score >= tesseract_score:
        return paddle_text
    return tesseract_text


def ocr_single_page(pdf_path: str, page_index: int, dpi: int = 250, lang: str = "es") -> str:
    """
    Convierte una sola página del PDF a imagen y aplica PaddleOCR + Tesseract.
    Elige automáticamente el mejor resultado.
    """
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_index + 1,
        last_page=page_index + 1,
    )

    if not images:
        return ""

    image = images[0]

    paddle_text = image_to_text_with_paddle(image, lang=lang)

    # Paddle usa "es", Tesseract usa "spa"
    tesseract_lang = "spa" if lang == "es" else lang
    tesseract_text = image_to_text_with_tesseract(image, lang=tesseract_lang)

    return choose_best_ocr_text(paddle_text, tesseract_text)


def ocr_pages(pdf_path: str, page_indices: list[int], dpi: int = 250, lang: str = "es") -> dict[int, str]:
    """
    Aplica OCR solo a las páginas solicitadas.
    Usa estrategia híbrida PaddleOCR + Tesseract.
    """
    result: dict[int, str] = {}

    for idx in page_indices:
        text = ocr_single_page(pdf_path, idx, dpi=dpi, lang=lang)
        if text:
            result[idx] = text

    return result


def extract_text_from_scanned_pdf(pdf_path: str, dpi: int = 250, lang: str = "es") -> str:
    """
    Convierte todo el PDF a imágenes y aplica OCR híbrido a cada página.
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    pages_text = []

    tesseract_lang = "spa" if lang == "es" else lang

    for image in images:
        paddle_text = image_to_text_with_paddle(image, lang=lang)
        tesseract_text = image_to_text_with_tesseract(image, lang=tesseract_lang)
        best_text = choose_best_ocr_text(paddle_text, tesseract_text)

        if best_text:
            pages_text.append(best_text)

    return "\n".join(pages_text).strip()