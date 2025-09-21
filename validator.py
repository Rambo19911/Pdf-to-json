# validator.py
import re
from typing import List, Dict, Any, Tuple

def validate_processed_data(data: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """Enhanced validation of processed data structure."""
    messages = []
    
    if not data:
        messages.append("Validācijas kļūda: Datu saraksts ir tukšs.")
        return False, messages

    # Check for law title
    missing_titles = sum(1 for item in data if not item.get("law_title") or item["law_title"] == "Nezinams_likums")
    if missing_titles > 0:
        messages.append(f"Brīdinājums: {missing_titles} ierakstiem trūkst likuma nosaukuma.")

    # Check content quality
    empty_content = sum(1 for item in data if not item.get("content", "").strip())
    if empty_content > 0:
        messages.append(f"Brīdinājums: {empty_content} ierakstiem ir tukšs saturs.")

    # Article sequence validation
    articles = []
    for i, item in enumerate(data):
        if item.get("article"):
            match = re.match(r'(\d+)', item["article"])
            if match:
                article_num = int(match.group(1))
                articles.append((article_num, i))

    if articles:
        articles.sort()
        prev_num = 0
        gaps = []
        
        for article_num, index in articles:
            if article_num < prev_num:
                messages.append(f"Validācijas kļūda: Pantu secība nav pareiza pie ieraksta Nr.{index+1}. Pants {article_num} seko pēc {prev_num}.")
            elif article_num > prev_num + 1:
                # Check for gaps
                for missing in range(prev_num + 1, article_num):
                    gaps.append(str(missing))
            prev_num = article_num
        
        if gaps:
            messages.append(f"Brīdinājums: Iespējami iztrūkstošie panti: {', '.join(gaps[:10])}{'...' if len(gaps) > 10 else ''}")

    # Structure validation
    orphaned_points = sum(1 for item in data if item.get("point") and not item.get("article"))
    if orphaned_points > 0:
        messages.append(f"Strukturāla kļūda: {orphaned_points} punkti bez panta atsauces.")

    orphaned_subpoints = sum(1 for item in data if item.get("subpoint") and not item.get("point"))
    if orphaned_subpoints > 0:
        messages.append(f"Strukturāla kļūda: {orphaned_subpoints} apakšpunkti bez punkta atsauces.")

    # Content length validation
    short_articles = sum(1 for item in data if item.get("article") and len(item.get("content", "")) < 10)
    if short_articles > 0:
        messages.append(f"Brīdinājums: {short_articles} panti ar ļoti īsu saturu (< 10 simboli).")

    has_errors = any("kļūda" in msg.lower() for msg in messages)
    
    if not messages:
        messages.append("Dati ir strukturāli derīgi un kvalitatīvi.")

    return not has_errors, messages

