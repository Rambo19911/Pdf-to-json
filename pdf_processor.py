# pdf_processor.py

import fitz
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from queue import Queue

def log_item(queue, text, tag):
    if queue:
        queue.put((text, tag))

# ... (extract_law_title funkcija paliek nemainīga) ...
def extract_law_title(page: fitz.Page, log_queue: Optional[Queue] = None) -> Optional[str]:
    full_text = page.get_text("text")
    match = re.search(r"izsludina šādu likumu:\s*\n\s*([A-ZĀČĒĢĪĶĻŅŠŪŽ\s]+likums)", full_text, re.IGNORECASE)
    if match:
        return re.sub(r'\s+', ' ', match.group(1).strip())
    blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_SEARCH)["blocks"]
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["lines"]:
                    if (span["flags"] & 2**4) and "likums" in span["text"].lower() and len(span["text"]) > 12:
                        return re.sub(r'\s+', ' ', span["text"].strip())
    return None

def process_pdf_to_structured_data(pdf_path: str, log_queue: Optional[Queue] = None) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    doc = fitz.open(pdf_path)
    structured_data = []
    law_title = "Nezinams_likums"

    if len(doc) > 0:
        title_candidate = extract_law_title(doc[0], log_queue)
        if title_candidate:
            law_title = title_candidate
    
    log_item(log_queue, f"{law_title}\n", 'title')
    time.sleep(0.5)

    current_context = {"article": None, "point": None, "subpoint": None}
    
    article_pattern = re.compile(r"^\s*(\d{1,3}[.¹]?\s*pants\.)\s*(.*)", re.IGNORECASE)
    point_pattern_paren = re.compile(r"^\s*\(([\d\w¹²³⁴⁵⁶⁷⁸⁹]+)\)\s*(.*)")
    point_subpoint_pattern_dot = re.compile(r"^\s*(\d{1,2})\)\s*(.*)")
    
    stop_keywords = ["pārejas noteikumi", "informatīvā atsauce uz eiropas savienības direktīvām"]
    stop_processing = False

    for i, page in enumerate(doc):
        if stop_processing: break
        log_item(log_queue, f"\n--- Lasa {i+1}. lapu ---\n", 'meta')
        
        # === JAUNĀ RINDIŅA PROGRESAM ===
        log_item(log_queue, "", "progress_update")
        time.sleep(0.2)

        page_rect, clip_rect = page.rect, fitz.Rect(page.rect.x0 + 50, page.rect.y0 + 50, page.rect.x1 - 50, page.rect.y1 - 50)
        
        for block in page.get_text("blocks", clip=clip_rect):
            # ... (pārējais kods šajā ciklā paliek nemainīgs) ...
            block_text = block[4]
            if any(keyword in block_text.lower() for keyword in stop_keywords):
                stop_processing = True
                break
            for line in block_text.strip().split('\n'):
                line = line.strip()
                if not line: continue
                time.sleep(0.02)
                article_match = article_pattern.match(line)
                point_match_paren = point_pattern_paren.match(line)
                point_subpoint_match = point_subpoint_pattern_dot.match(line)
                new_entry = None
                if article_match:
                    current_context = {"article": article_match.group(1).strip(), "point": None, "subpoint": None}
                    content = article_match.group(2).strip()
                    log_item(log_queue, f"{current_context['article']} {content}\n", 'article')
                    new_entry = {"law_title": law_title, "article": current_context["article"], "point": None, "subpoint": None, "content": content}
                elif point_match_paren and current_context["article"]:
                    current_context["point"] = point_match_paren.group(1).strip()
                    current_context["subpoint"] = None
                    content = point_match_paren.group(2).strip()
                    log_item(log_queue, f"({current_context['point']}) {content}\n", 'point')
                    new_entry = {"law_title": law_title, "article": current_context["article"], "point": current_context["point"], "subpoint": None, "content": content}
                elif point_subpoint_match and current_context["article"]:
                    content = point_subpoint_match.group(2).strip()
                    if not current_context["point"]:
                        current_context["point"] = point_subpoint_match.group(1).strip()
                        log_item(log_queue, f"{current_context['point']}) {content}\n", 'point')
                        new_entry = {"law_title": law_title, "article": current_context["article"], "point": current_context["point"], "subpoint": None, "content": content}
                    else:
                        current_context["subpoint"] = point_subpoint_match.group(1).strip()
                        log_item(log_queue, f"{current_context['subpoint']}) {content}\n", 'subpoint')
                        new_entry = {"law_title": law_title, "article": current_context["article"], "point": current_context["point"], "subpoint": current_context["subpoint"], "content": content}
                else:
                    if structured_data and line:
                        log_item(log_queue, f"{line} ", 'content')
                        structured_data[-1]["content"] += " " + line
                if new_entry:
                    if not new_entry["content"]: new_entry["content"] = ""
                    structured_data.append(new_entry)

    doc.close()
    return law_title, structured_data