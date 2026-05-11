import re
import unicodedata


def normalize_unicode(text: str) -> str:
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text)


def normalize_line_breaks(text: str) -> str:
    if not text:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def remove_non_informative_chars(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\x00", " ").replace("\ufeff", " ")
    return text


def remove_extra_spaces(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    text = normalize_unicode(text)
    text = normalize_line_breaks(text)
    text = remove_non_informative_chars(text)
    text = remove_extra_spaces(text)
    return text.strip()
