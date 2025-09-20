# verify_last_file.py

import os
import shutil
import json
import fitz  # PyMuPDF
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from config import path_config

# Žurnalēšanas iestatīšana
log_file_handler = logging.FileHandler(path_config.log_file, mode='a', encoding='utf-8')
log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - VERIFY - %(message)s'))
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(log_file_handler)
    logger.addHandler(logging.StreamHandler())

def find_latest_processed_files() -> Tuple[Path | None, Path | None]:
    """Atrod pēdējos apstrādātos JSON un PDF failus."""
    try:
        json_files = sorted(path_config.processed_json_dir.glob('*.json'), key=os.path.getmtime, reverse=True)
        if not json_files: return None, None
        latest_json = json_files[0]
        corresponding_pdf = path_config.processed_pdfs_dir / f"{latest_json.stem}.pdf"
        return (latest_json, corresponding_pdf) if corresponding_pdf.exists() else (latest_json, None)
    except Exception as e:
        logger.error(f"Kļūda meklējot failus: {e}")
        return None, None

def get_article_text_from_pdf(pdf_text: str, article_num: int) -> str:
    """Iegūst pilnu, neapstrādātu tekstu konkrētam pantam no PDF kopējā teksta."""
    start_pattern = re.compile(fr"^\s*({article_num}[.¹]?\s*pants\.)", re.MULTILINE | re.IGNORECASE)
    start_match = start_pattern.search(pdf_text)
    if not start_match: return ""

    next_article_num = article_num + 1
    end_pattern = re.compile(fr"^\s*({next_article_num}[.¹]?\s*pants\.)", re.MULTILINE | re.IGNORECASE)
    end_match = end_pattern.search(pdf_text, pos=start_match.end())

    start_index = start_match.start()
    end_index = end_match.start() if end_match else len(pdf_text)
    
    stop_pattern = re.compile(r"pārejas noteikumi|informatīvā atsauce", re.IGNORECASE | re.MULTILINE)
    stop_match = stop_pattern.search(pdf_text, pos=start_index)
    if stop_match and (not end_match or stop_match.start() < end_index):
        end_index = stop_match.start()
        
    return pdf_text[start_index:end_index].strip()

def clean_text(text: str) -> str:
    """Attīra tekstu salīdzināšanai (noņem atstarpes, pieturzīmes utt.)."""
    return re.sub(r'[\s\W_]+', '', text, flags=re.UNICODE).lower()

def verify_content_integrity(json_data: List[Dict[str, Any]], pdf_path: Path) -> List[str]:
    """Salīdzina JSON saturu ar PDF oriģinālu, lai atrastu iztrūkstošu vai nepareizi grupētu tekstu."""
    findings = []
    try:
        doc = fitz.open(pdf_path)
        pdf_text = "".join([page.get_text("text") for page in doc])
        doc.close()

        json_articles = {}
        for item in json_data:
            article = item.get("article")
            if article and item.get("content"):
                json_articles.setdefault(article, "")
                json_articles[article] += " " + item["content"]

        for article, json_content in json_articles.items():
            match = re.match(r'(\d+)', article)
            if not match: continue
            
            article_num = int(match.group(1))
            pdf_article_text = get_article_text_from_pdf(pdf_text, article_num)
            
            clean_json_content = clean_text(json_content)
            clean_pdf_content = clean_text(pdf_article_text)

            if len(clean_json_content) < len(clean_pdf_content) * 0.95: # 5% tolerance
                findings.append(f"Iespējams, trūkst saturs pantā '{article}'. JSON versija ir ievērojami īsāka par PDF oriģinālu.")
    except Exception as e:
        findings.append(f"Kļūda satura integritātes pārbaudē: {e}")
    return findings

def verify_article_sequence(json_data: List[Dict[str, Any]]) -> List[str]:
    """Pārbauda, vai pantu numerācija ir secīga."""
    try:
        numbers = sorted([int(m.group(1)) for item in json_data if item.get("article") and (m := re.match(r'(\d+)', item["article"]))])
        if not numbers: return []
        missing = [str(i) for i in range(numbers[0], numbers[-1] + 1) if i not in numbers]
        return [f"Iespējams, trūkst panti: {', '.join(missing)}."] if missing else []
    except Exception as e:
        return [f"Neizdevās pārbaudīt pantu secību: {e}"]

def main():
    logger.info("Sāk pēdējā faila verifikāciju ar dziļo satura analīzi...")
    latest_json, latest_pdf = find_latest_processed_files()

    if not latest_json or not latest_pdf:
        logger.info("Nav failu, ko pārbaudīt.")
        return

    logger.info(f"Pārbauda: '{latest_json.name}' pret '{latest_pdf.name}'")

    try:
        with open(latest_json, 'r', encoding='utf-8') as f: data = json.load(f)
    except Exception as e:
        logger.error(f"Nevarēja nolasīt JSON failu '{latest_json.name}': {e}")
        return

    critical_findings = verify_article_sequence(data) + verify_content_integrity(data, latest_pdf)

    if not critical_findings:
        logger.info("✅ Verifikācija pabeigta. Kritiskas nepilnības netika atklātas.")
    else:
        report = "\n" + "="*60 + "\n⚠️  VERIFIKĀCIJAS ZIŅOJUMS: ATRSTAS KRITISKAS KĻŪDAS\n" + "="*60
        for i, finding in enumerate(critical_findings, 1): report += f"\n{i}. {finding}"
        report += "\n" + "="*60
        print(report)
        logger.error("Atrastas kritiskas nepilnības:" + "".join([f"\n- {f}" for f in critical_findings]))
        
        choice = input(f"\nVai nosūtīt '{latest_pdf.name}' atpakaļ otreizējai apstrādei? (y/n): ").lower().strip()
        logger.info(f"Lietotāja izvēle: '{choice}'")
        
        if choice == 'y':
            try:
                shutil.move(str(latest_pdf), path_config.input_dir / latest_pdf.name)
                os.remove(latest_json)
                logger.info(f"Fails '{latest_pdf.name}' pārvietots atpakaļ. JSON fails '{latest_json.name}' izdzēsts.")
            except Exception as e:
                logger.error(f"Kļūda, pārvietojot failus: {e}")
        else:
            logger.info("Darbība atcelta.")

if __name__ == "__main__":
    main()

