# main.py

import json
import shutil
import logging
import re
import os
from pathlib import Path
from typing import List, Optional
from queue import Queue
from config import path_config
from pdf_processor import process_pdf_to_structured_data
from validator import validate_processed_data

# Setup logging
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
    """Clean filename from illegal characters with improved handling."""
    # Remove illegal characters and replace spaces
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name)
    clean_name = re.sub(r'\s+', "_", clean_name)
    
    # Ensure reasonable length
    if len(clean_name) > 200:
        clean_name = clean_name[:200]
    
    # Ensure it doesn't end with dots or spaces
    clean_name = clean_name.strip('. ')
    
    return clean_name if clean_name else "Nezinams_likums"

def backup_existing_file(filepath: Path) -> bool:
    """Create backup if file already exists."""
    if filepath.exists():
        try:
            backup_path = filepath.with_suffix(f'.backup{filepath.suffix}')
            shutil.copy2(filepath, backup_path)
            logger.info(f"Izveidota rezerves kopija: {backup_path.name}")
            return True
        except Exception as e:
            logger.warning(f"Neizdevās izveidot rezerves kopiju: {e}")
            return False
    return True

def run_processing_for_list(pdf_files: List[Path], log_queue: Optional[Queue] = None):
    """Process list of PDF files with enhanced error handling."""
    
    def log(message, tag='meta'):
        logger.info(message.strip())
        if log_queue:
            log_queue.put((message + "\n", tag))

    # Validate files before processing
    valid_files = []
    for pdf_file in pdf_files:
        is_valid, error_msg = path_config.validate_file(pdf_file)
        if is_valid:
            valid_files.append(pdf_file)
        else:
            log(f"Izlaists fails {pdf_file.name}: {error_msg}", 'error')

    if not valid_files:
        log("Nav derīgu failu apstrādei!", 'error')
        return

    log(f"Apstrādei atlasīti {len(valid_files)} no {len(pdf_files)} failiem", 'meta')

    for i, pdf_file in enumerate(valid_files, 1):
        log(f"\n=== FAILS {i}/{len(valid_files)}: {pdf_file.name} ===", 'meta')
        
        input_pdf_path = None
        try:
            # Copy to input directory if needed
            input_pdf_path = path_config.input_dir / pdf_file.name
            if not input_pdf_path.exists():
                shutil.copy2(pdf_file, input_pdf_path)
                log(f"Fails nokopēts uz apstrādes mapi", 'meta')

            # Process PDF
            log("Sāk PDF analīzi...", 'meta')
            law_title, structured_data = process_pdf_to_structured_data(str(input_pdf_path), log_queue)
            
            if not law_title or not structured_data:
                raise ValueError("Neizdevās iegūt likuma nosaukumu vai strukturēt datus.")
            
            log(f"Iegūts likuma nosaukums: {law_title}", 'meta')
            log(f"Izveidoti {len(structured_data)} strukturēti ieraksti", 'meta')

            # Validate data
            log("Validē strukturētos datus...", 'meta')
            is_valid, messages = validate_processed_data(structured_data)
            
            for msg in messages:
                log(f"Validācija: {msg}", 'meta' if not any(word in msg.lower() for word in ['kļūda', 'error']) else 'error')

            # Save JSON file
            safe_title = sanitize_filename(law_title)
            json_filename = f"{safe_title}.json"
            json_filepath = path_config.processed_json_dir / json_filename
            
            # Backup existing file if needed
            backup_existing_file(json_filepath)
            
            log("Saglabā JSON failu...", 'meta')
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
            
            log(f"JSON fails saglabāts: {json_filename}", 'meta')

            # Move processed PDF
            processed_pdf_path = path_config.processed_pdfs_dir / f"{safe_title}.pdf"
            backup_existing_file(processed_pdf_path)
            
            shutil.move(str(input_pdf_path), processed_pdf_path)
            log(f"PDF fails pārvietots uz: {processed_pdf_path.name}", 'meta')
            
            log(f"✅ Veiksmīgi pabeigts: {pdf_file.name}", 'meta')

        except Exception as e:
            error_msg = f"KĻŪDA apstrādājot {pdf_file.name}: {str(e)}"
            log(error_msg, 'error')
            
            # Move to error directory
            error_path = path_config.error_dir / pdf_file.name
            try:
                if input_pdf_path and input_pdf_path.exists():
                    shutil.move(str(input_pdf_path), error_path)
                    log(f"Fails pārvietots uz kļūdu mapi: {error_path.name}", 'error')
                elif pdf_file != error_path:
                    shutil.copy2(pdf_file, error_path)
                    log(f"Fails nokopēts uz kļūdu mapi: {error_path.name}", 'error')
            except Exception as move_error:
                log(f"Neizdevās pārvietot failu uz kļūdu mapi: {move_error}", 'error')

    log(f"\n🏁 Apstrāde pabeigta. Veiksmīgi: {len(valid_files)} faili", 'meta')

def main():
    """Main function for standalone execution."""
    logger.info("Sāk PDF failu apstrādi no 'input_pdfs' mapes...")
    
    if not path_config.setup_directories():
        logger.error("Neizdevās izveidot nepieciešamās mapes!")
        return
    
    input_files = list(path_config.input_dir.glob("*.pdf"))
    
    if not input_files:
        logger.info("Nav PDF failu apstrādei 'input_pdfs' mapē.")
        return
    
    run_processing_for_list(input_files)
    logger.info("Visi faili apstrādāti.")

if __name__ == "__main__":
    main()