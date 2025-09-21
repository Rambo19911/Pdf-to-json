"""alt_extractor.py

Papildu PDF teksta ieguves un analizēšanas funkcijas, kas izmanto pdfplumber
kā alternatīvu PyMuPDF (fitz). Šo moduli var izmantot kā rezerves mehānismu
vai rezultātu salīdzināšanai, lai uzlabotu ekstrakcijas precizitāti.

Šobrīd tiek nodrošinātas tikai dažas pamatfunkcijas (pirmajā kārtā vajadzīgās
mūsu projektam), taču arhitektūra ļauj vēlāk viegli pievienot plašāku
salīdzināšanas un sapludināšanas loģiku.
"""
from __future__ import annotations

from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

import pdfplumber

__all__ = [
    "extract_first_page_text",
    "extract_law_title_pdfplumber",
    "get_page_texts",
]


# ------------------------------------------------------------
#  Teksta ieguves palīgfunkcijas
# ------------------------------------------------------------

def extract_first_page_text(pdf_path: str | Path) -> str:
    """Atgriež pirmās lapas pliku tekstu, izmantojot pdfplumber.

    Ja notiek kļūda (piem., bojāts fails), tiek atgriezts tukšs
    virkne, kas ļauj aicinātāju pašam izlemt, ko darīt tālāk.
    """
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            if not doc.pages:
                return ""
            first_page = doc.pages[0]
            text = first_page.extract_text() or ""
            return text
    except Exception:
        return ""


def get_page_texts(pdf_path: str | Path) -> List[str]:
    """Atgriež visu lapu tekstu sarakstu, izmantojot pdfplumber.

    Šo funkciju var izmantot dziļākai salīdzināšanai ar PyMuPDF
    rezultātiem vai rezerves gadījumos, kad zivju fails neļaujas
    PyMuPDF parserim.
    """
    texts: List[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            for page in doc.pages:
                texts.append(page.extract_text() or "")
    except Exception:
        # Kļūdas gadījumā atgriežam tik, cik paspēts
        pass
    return texts


# ------------------------------------------------------------
#  Juridiskā nosaukuma atpazīšana (fallback)
# ------------------------------------------------------------

import re

TITLE_PATTERNS = [
    # Pirmā izvēle – līdzīgi kā PyMuPDF funkcijā, bet pdfplumber izvada
    # mazliet citāku formatējumu.
    re.compile(
        r"izsludina\s+šādu\s+likumu:\s*([A-ZĀČĒĢĪĶĻŅŠŪŽ\s]+likums)",
        flags=re.IGNORECASE,
    ),
    # Vispārīga MINICOM rakstība: lielie burti + LIKUMS vārda galā
    re.compile(r"^([A-ZĀČĒĢĪĶĻŅŠŪŽ][A-ZĀČĒĢĪĶĻŅŠŪŽ\s]{10,}LIKUMS)$", re.MULTILINE),
    # Lielie, tad likums mazajiem (biežāk pdfplumber atgriež)
    re.compile(r"^([A-ZĀČĒĢĪĶĻŅŠŪŽ\s]+likums)\s*$", re.MULTILINE | re.IGNORECASE),
]


def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def extract_law_title_pdfplumber(pdf_path: str | Path) -> Optional[str]:
    """Mēģina atrast likuma nosaukumu PDF pirmajā lapā, izmantojot pdfplumber.

    Atgriež nosaukumu vai None, ja neizdodas neko atrast.
    """
    first_page_text = extract_first_page_text(pdf_path)
    if not first_page_text:
        return None

    for pattern in TITLE_PATTERNS:
        match = pattern.search(first_page_text)
        if match:
            return _normalize_whitespace(match.group(1))
    return None


# ------------------------------------------------------------
#  Vienkārša satura salīdzināšana
# ------------------------------------------------------------

def texts_are_similar(t1: str, t2: str, threshold: float = 0.9) -> bool:
    """Pārbauda, vai divas teksta virknes ir >= threshold līdzīgas."""
    if not t1 or not t2:
        return False
    ratio = SequenceMatcher(None, t1, t2).ratio()
    return ratio >= threshold
