# pdf_processor.py

import fitz
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from queue import Queue
import logging

def log_item(queue, text, tag):
    if queue:
        queue.put((text, tag))

def extract_law_title(page: fitz.Page, log_queue: Optional[Queue] = None) -> Optional[str]:
    """Extract law title with improved pattern matching."""
    try:
        full_text = page.get_text("text")
        
        # Primary pattern - look for "izsludina šādu likumu:"
        match = re.search(r"izsludina šādu likumu:\s*\n\s*([A-ZĀČĒĢĪĶĻŅŠŪŽ\s]+likums)", full_text, re.IGNORECASE)
        if match:
            return re.sub(r'\s+', ' ', match.group(1).strip())
        
        # Secondary pattern - look for standalone law titles
        title_patterns = [
            r"^([A-ZĀČĒĢĪĶĻŅŠŪŽ][A-ZĀČĒĢĪĶĻŅŠŪŽ\s]{10,}LIKUMS)$",
            r"^([A-ZĀČĒĢĪĶĻŅŠŪŽ\s]+likums)\s*$"
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, full_text, re.MULTILINE | re.IGNORECASE)
            if match:
                return re.sub(r'\s+', ' ', match.group(1).strip())
        
        # Fallback - use text block analysis
        blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_SEARCH)["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span.get("text", "")
                        if (span["flags"] & 16) and "likums" in text.lower() and len(text) > 12:
                            return re.sub(r'\s+', ' ', text.strip())
    except Exception as e:
        log_item(log_queue, f"Kļūda likuma nosaukuma ekstraktēšanā: {e}", 'error')
    
    return None

def process_pdf_to_structured_data(pdf_path: str, log_queue: Optional[Queue] = None) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Process PDF with improved error handling and performance."""
    doc = None
    try:
        doc = fitz.open(pdf_path)
        structured_data = []
        law_title = "Nezinams_likums"

        if len(doc) > 0:
            title_candidate = extract_law_title(doc[0], log_queue)
            if title_candidate:
                law_title = title_candidate
        
        log_item(log_queue, f"{law_title}\n", 'title')
        time.sleep(0.1)  # Reduced delay for better performance

        current_context = {"article": None, "point": None, "subpoint": None}
        
        # Compiled regex patterns for better performance
        article_pattern = re.compile(r"^\s*(\d{1,3}[.¹]?\s*pants\.)\s*(.*)", re.IGNORECASE)
        point_pattern_paren = re.compile(r"^\s*\(([\d\w¹²³⁴⁵⁶⁷⁸⁹]+)\)\s*(.*)")
        point_subpoint_pattern_dot = re.compile(r"^\s*(\d{1,2})\)\s*(.*)")
        
        stop_keywords = ["pārejas noteikumi", "informatīvā atsauce uz eiropas savienības direktīvām"]
        stop_processing = False

        for i, page in enumerate(doc):
            if stop_processing: 
                break
                
            log_item(log_queue, f"\n--- Lasa {i+1}. lapu ---\n", 'meta')
            log_item(log_queue, "", "progress_update")
            time.sleep(0.05)  # Reduced delay

            try:
                page_rect = page.rect
                clip_rect = fitz.Rect(page_rect.x0 + 50, page_rect.y0 + 50, 
                                    page_rect.x1 - 50, page_rect.y1 - 50)
                
                blocks = page.get_text("blocks", clip=clip_rect)
                
                for block in blocks:
                    if len(block) < 5:
                        continue
                        
                    block_text = block[4]
                    if any(keyword in block_text.lower() for keyword in stop_keywords):
                        stop_processing = True
                        break
                    
                    for line in block_text.strip().split('\n'):
                        line = line.strip()
                        if not line: 
                            continue
                        
                        # Process different types of content
                        new_entry = None
                        
                        article_match = article_pattern.match(line)
                        if article_match:
                            current_context = {
                                "article": article_match.group(1).strip(), 
                                "point": None, 
                                "subpoint": None
                            }
                            content = article_match.group(2).strip()
                            log_item(log_queue, f"{current_context['article']} {content}\n", 'article')
                            new_entry = {
                                "law_title": law_title, 
                                "article": current_context["article"], 
                                "point": None, 
                                "subpoint": None, 
                                "content": content
                            }
                        else:
                            point_match_paren = point_pattern_paren.match(line)
                            if point_match_paren and current_context["article"]:
                                current_context["point"] = point_match_paren.group(1).strip()
                                current_context["subpoint"] = None
                                content = point_match_paren.group(2).strip()
                                log_item(log_queue, f"({current_context['point']}) {content}\n", 'point')
                                new_entry = {
                                    "law_title": law_title, 
                                    "article": current_context["article"], 
                                    "point": current_context["point"], 
                                    "subpoint": None, 
                                    "content": content
                                }
                            else:
                                point_subpoint_match = point_subpoint_pattern_dot.match(line)
                                if point_subpoint_match and current_context["article"]:
                                    content = point_subpoint_match.group(2).strip()
                                    if not current_context["point"]:
                                        current_context["point"] = point_subpoint_match.group(1).strip()
                                        log_item(log_queue, f"{current_context['point']}) {content}\n", 'point')
                                        new_entry = {
                                            "law_title": law_title, 
                                            "article": current_context["article"], 
                                            "point": current_context["point"], 
                                            "subpoint": None, 
                                            "content": content
                                        }
                                    else:
                                        current_context["subpoint"] = point_subpoint_match.group(1).strip()
                                        log_item(log_queue, f"{current_context['subpoint']}) {content}\n", 'subpoint')
                                        new_entry = {
                                            "law_title": law_title, 
                                            "article": current_context["article"], 
                                            "point": current_context["point"], 
                                            "subpoint": current_context["subpoint"], 
                                            "content": content
                                        }
                                else:
                                    # Continuation text
                                    if structured_data and line:
                                        log_item(log_queue, f"{line} ", 'content')
                                        structured_data[-1]["content"] += " " + line
                        
                        if new_entry:
                            if not new_entry["content"]: 
                                new_entry["content"] = ""
                            structured_data.append(new_entry)
                            
            except Exception as e:
                log_item(log_queue, f"Kļūda apstrādājot {i+1}. lapu: {e}\n", 'error')
                continue

        return law_title, structured_data
        
    except Exception as e:
        log_item(log_queue, f"Kritiska kļūda PDF apstrādē: {e}\n", 'error')
        return None, []
    finally:
        if doc:
            doc.close()