# main.py

import json
import shutil
import logging
import re
from pathlib import Path
from typing import List, Optional
from queue import Queue # Importējam Queue
from config import path_config
from pdf_processor import process_pdf_to_structured_data
from validator import validate_processed_data

# ... (pārējais kods līdz `run_processing_for_list` paliek nemainīgs) ...
path_config.setup_directories()
log_handler = logging.FileHandler(path_config.log_file, mode='a', encoding='utf-8')
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - MAIN - %(message)s')
log_handler.setFormatter(log_formatter)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(log_handler)
    logger.addHandler(logging.StreamHandler())

def sanitize_filename(name: str) -> str:
    """Attīra faila nosaukumu no neatļautiem simboliem."""
    return re.sub(r'[\\/*?:"<>|]', "", name).replace(" ", "_")

def run_processing_for_list(pdf_files: List[Path], log_queue: Optional[Queue] = None):
    """Apstrādā sarakstā norādītos PDF failus, izmantojot 'queue' ziņojumiem."""
    
    def log(message, tag='meta'):
        logger.info(message)
        if log_queue:
            log_queue.put((message + "\n", tag))

    for pdf_file in pdf_files:
        log(f"\n=================================\n--- SĀK APSTRĀDĀT: {pdf_file.name} ---\n=================================", 'meta')
        try:
            input_pdf_path = path_config.input_dir / pdf_file.name
            if not input_pdf_path.exists():
                shutil.copy(pdf_file, input_pdf_path)

            law_title, structured_data = process_pdf_to_structured_data(str(input_pdf_path), log_queue)
            
            if not law_title or not structured_data:
                raise ValueError("Neizdevās iegūt likuma nosaukumu vai strukturēt datus.")
            
            log(f"\nValidē strukturētos datus...", 'meta')
            is_valid, messages = validate_processed_data(structured_data)
            for msg in messages:
                log(f"Validācija: {msg}", 'meta' if is_valid else 'error')

            log("Saglabā datus JSON failā...", 'meta')
            safe_title = sanitize_filename(law_title)
            json_filename = f"{safe_title}.json"
            json_filepath = path_config.processed_json_dir / json_filename
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=4)
            log(f"Dati saglabāti: {json_filepath.name}", 'meta')

            log("Pārvieto apstrādāto PDF failu...", 'meta')
            processed_pdf_path = path_config.processed_pdfs_dir / f"{safe_title}.pdf"
            shutil.move(str(input_pdf_path), processed_pdf_path)
            log(f"PDF fails pārvietots.", 'meta')

        except Exception as e:
            log(f"KĻŪDA apstrādājot {pdf_file.name}: {e}", 'error')
            error_path = path_config.error_dir / pdf_file.name
            if input_pdf_path.exists():
                shutil.move(str(input_pdf_path), error_path)
                log(f"Fails pārvietots uz kļūdu mapi.", 'error')
        
        log(f"--- PABEIGTA APSTRĀDE failam: {pdf_file.name} ---", 'meta')

def main():
    logger.info("Sāk PDF failu apstrādi no 'input_pdfs' mapes...")
    input_files = list(path_config.input_dir.glob("*.pdf"))
    run_processing_for_list(input_files)
    logger.info("Visi faili apstrādāti.")

if __name__ == "__main__":
    main()