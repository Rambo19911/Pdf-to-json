"""legal_parser.py

Noteikumu un palīgfunkciju kopa latviešu juridisko dokumentu
strukturēšanai. Šeit nav izmantoti ārēji NLP modeļi – visa loģika
balstās regulārajās izteiksmēs un noderīgu atslēgvārdu sarakstos.
"""
from __future__ import annotations

import re
from typing import List

# ------------------------------------------------------------
#  Regulārās izteiksmes pamatstruktūrai
# ------------------------------------------------------------

ARTICLE_PATTERN = re.compile(r"^\s*(\d{1,3}[.¹]?\s*pants\.)\s*(.*)", re.IGNORECASE)
POINT_PATTERN_PAREN = re.compile(r"^\s*\(([\d\w¹²³⁴⁵⁶⁷⁸⁹]+)\)\s*(.*)")
POINT_SUBPOINT_PATTERN_DOT = re.compile(r"^\s*(\d{1,2})\)\s*(.*)")

# Atslēgvārdi, pie kuriem jāpārtrauc struktūras analīze (parasti nav vairs pantus)
STOP_KEYWORDS: List[str] = [
    "pārejas noteikumi",
    "informatīvā atsauce uz eiropas savienības direktīvām",
    "informatīvā atsauce",
    "pielikums",
]

__all__ = [
    "ARTICLE_PATTERN",
    "POINT_PATTERN_PAREN",
    "POINT_SUBPOINT_PATTERN_DOT",
    "STOP_KEYWORDS",
]
