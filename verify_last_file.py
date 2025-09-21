# verify_last_file.py

import os
import shutil
import json
import fitz  # PyMuPDF
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from config import path_config

# Enhanced logging setup
def setup_logging():
    """Setup logging with proper formatting."""
    log_file_handler = logging.FileHandler(path_config.log_file, mode='a', encoding='utf-8')
    log_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - VERIFY - %(message)s'))
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        logger.addHandler(log_file_handler)
        logger.addHandler(logging.StreamHandler())
    
    return logger

logger = setup_logging()

def extract_page_text_compat(page) -> str:
    """Safely extract page text across PyMuPDF versions without tripping type checkers."""
    try:
        get_text = getattr(page, "get_text", None)
        if callable(get_text):
            return get_text()  # default mode is plain text
        getText = getattr(page, "getText", None)
        if callable(getText):
            return getText()  # legacy fallback
    except Exception:
        pass
    return ""

def find_latest_processed_files() -> Tuple[Optional[Path], Optional[Path]]:
    """Find the most recently processed JSON and PDF files with better error handling."""
    try:
        if not path_config.processed_json_dir.exists():
            logger.warning("JSON directory doesn't exist")
            return None, None
            
        json_files = sorted(
            path_config.processed_json_dir.glob('*.json'), 
            key=lambda x: x.stat().st_mtime, 
            reverse=True
        )
        
        if not json_files:
            logger.info("No JSON files found for verification")
            return None, None
            
        latest_json = json_files[0]
        corresponding_pdf = path_config.processed_pdfs_dir / f"{latest_json.stem}.pdf"
        
        if not corresponding_pdf.exists():
            logger.warning(f"Corresponding PDF not found: {corresponding_pdf.name}")
            return latest_json, None
            
        return latest_json, corresponding_pdf
        
    except Exception as e:
        logger.error(f"Error finding latest files: {e}")
        return None, None

def get_article_text_from_pdf(pdf_text: str, article_num: int) -> str:
    """Extract complete, unprocessed text for specific article with improved pattern matching."""
    try:
        # More robust article pattern matching
        start_patterns = [
            fr"^\s*({article_num}[.¹]?\s*pants\.)",
            fr"^\s*({article_num}\.\s*pants\.)",
            fr"^\s*({article_num}\s*pants\.)"
        ]
        
        start_match = None
        for pattern in start_patterns:
            start_match = re.search(pattern, pdf_text, re.MULTILINE | re.IGNORECASE)
            if start_match:
                break
                
        if not start_match:
            return ""

        # Find next article
        next_article_num = article_num + 1
        end_patterns = [
            fr"^\s*({next_article_num}[.¹]?\s*pants\.)",
            fr"^\s*({next_article_num}\.\s*pants\.)",
            fr"^\s*({next_article_num}\s*pants\.)"
        ]
        
        end_match = None
        for pattern in end_patterns:
            end_match = re.search(pattern, pdf_text, re.MULTILINE | re.IGNORECASE)
            if end_match:
                break

        start_index = start_match.start()
        end_index = end_match.start() if end_match else len(pdf_text)
        
        # Check for document end markers
        stop_patterns = [
            r"pārejas noteikumi",
            r"informatīvā atsauce",
            r"pielikums",
            r"ministru kabineta noteikumi"
        ]
        
        for stop_pattern in stop_patterns:
            stop_match = re.search(stop_pattern, pdf_text[start_index:], re.IGNORECASE | re.MULTILINE)
            if stop_match and (not end_match or stop_match.start() + start_index < end_index):
                end_index = stop_match.start() + start_index
                break
            
        return pdf_text[start_index:end_index].strip()
        
    except Exception as e:
        logger.error(f"Error extracting article {article_num}: {e}")
        return ""

def clean_text_for_comparison(text: str) -> str:
    """Clean text for comparison with improved normalization."""
    if not text:
        return ""
        
    # Normalize whitespace and remove special characters
    cleaned = re.sub(r'\s+', ' ', text)
    cleaned = re.sub(r'[^\w\s]', '', cleaned, flags=re.UNICODE)
    cleaned = cleaned.lower().strip()
    
    return cleaned

def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate simple similarity between two texts."""
    if not text1 or not text2:
        return 0.0
        
    clean1 = clean_text_for_comparison(text1)
    clean2 = clean_text_for_comparison(text2)
    
    if not clean1 or not clean2:
        return 0.0
    
    # Simple character-based similarity
    longer = max(len(clean1), len(clean2))
    shorter = min(len(clean1), len(clean2))
    
    if longer == 0:
        return 1.0
    
    return shorter / longer

def verify_content_integrity(json_data: List[Dict[str, Any]], pdf_path: Path) -> List[str]:
    """Compare JSON content with PDF original with enhanced analysis."""
    findings = []
    
    try:
        logger.info("Starting content integrity verification...")
        
        pdf_text = ""
        try:
            with fitz.open(pdf_path) as doc:
                # Use compatibility helper to avoid direct attribute access issues
                pdf_text = "".join(extract_page_text_compat(page) for page in doc)
        except Exception as e:
            logger.error(f"Failed to open or read PDF: {e}")
            findings.append("PDF text extraction failed or document is empty")
            return findings
        
        if not pdf_text.strip():
            findings.append("PDF text extraction failed or document is empty")
            return findings

        # Group JSON data by articles
        json_articles = {}
        for item in json_data:
            article = item.get("article")
            if article and item.get("content"):
                if article not in json_articles:
                    json_articles[article] = []
                json_articles[article].append(item["content"])

        # Combine content for each article
        for article in json_articles:
            json_articles[article] = " ".join(json_articles[article])

        logger.info(f"Comparing {len(json_articles)} articles...")
        
        similarity_threshold = path_config.content_similarity_threshold
        problematic_articles = []
        
        for article, json_content in json_articles.items():
            match = re.match(r'(\d+)', article)
            if not match:
                continue
            
            article_num = int(match.group(1))
            pdf_article_text = get_article_text_from_pdf(pdf_text, article_num)
            
            if not pdf_article_text:
                findings.append(f"Article '{article}' not found in PDF text")
                continue
            
            similarity = calculate_similarity(json_content, pdf_article_text)
            
            if similarity < similarity_threshold:
                problematic_articles.append((article, similarity))
                findings.append(
                    f"Content mismatch in '{article}': similarity {similarity:.2%} "
                    f"(threshold: {similarity_threshold:.2%})"
                )

        if problematic_articles:
            logger.warning(f"Found {len(problematic_articles)} articles with content issues")
        else:
            logger.info("All articles passed content integrity check")
            
    except Exception as e:
        findings.append(f"Error during content integrity verification: {e}")
        logger.error(f"Content verification error: {e}")
    
    return findings

def verify_article_sequence(json_data: List[Dict[str, Any]]) -> List[str]:
    """Verify article numbering sequence with enhanced checking."""
    findings = []
    
    try:
        # Extract article numbers
        article_numbers = []
        for item in json_data:
            article = item.get("article")
            if article:
                match = re.match(r'(\d+)', article)
                if match:
                    article_numbers.append(int(match.group(1)))
        
        if not article_numbers:
            findings.append("No articles found for sequence verification")
            return findings
        
        article_numbers = sorted(list(set(article_numbers)))  # Remove duplicates and sort
        
        if len(article_numbers) < 2:
            return findings  # Can't verify sequence with less than 2 articles
        
        # Check for gaps
        missing_articles = []
        for i in range(article_numbers[0], article_numbers[-1] + 1):
            if i not in article_numbers:
                missing_articles.append(i)
        
        if missing_articles:
            if len(missing_articles) <= 10:
                findings.append(f"Missing articles: {', '.join(map(str, missing_articles))}")
            else:
                findings.append(f"Many missing articles ({len(missing_articles)}): "
                              f"{', '.join(map(str, missing_articles[:10]))}...")
        
        logger.info(f"Article sequence check: {len(article_numbers)} articles, "
                   f"{len(missing_articles)} gaps")
                   
    except Exception as e:
        findings.append(f"Error verifying article sequence: {e}")
        logger.error(f"Sequence verification error: {e}")
    
    return findings

def interactive_reprocess_decision(pdf_path: Path, json_path: Path) -> bool:
    """Handle user decision for reprocessing with better UX."""
    try:
        print(f"\n{'='*60}")
        print("🔄 REPROCESSING OPTIONS")
        print(f"{'='*60}")
        print(f"PDF File: {pdf_path.name}")
        print(f"JSON File: {json_path.name}")
        print("\nOptions:")
        print("  y/yes - Move PDF back for reprocessing and delete JSON")
        print("  n/no  - Keep files as they are")
        print("  q/quit - Exit verification")
        print(f"{'='*60}")
        
        while True:
            choice = input("\nYour choice (y/n/q): ").lower().strip()
            
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            elif choice in ['q', 'quit']:
                logger.info("User chose to exit verification")
                exit(0)
            else:
                print("Please enter 'y', 'n', or 'q'")
                
    except KeyboardInterrupt:
        logger.info("Verification interrupted by user")
        exit(0)
    except Exception as e:
        logger.error(f"Error in interactive decision: {e}")
        return False

def reprocess_files(pdf_path: Path, json_path: Path) -> bool:
    """Move files for reprocessing with better error handling."""
    try:
        # Move PDF back to input directory
        target_pdf = path_config.input_dir / pdf_path.name
        
        # Handle existing file in input directory
        if target_pdf.exists():
            backup_name = f"{pdf_path.stem}_backup_{int(os.path.getmtime(target_pdf))}.pdf"
            backup_path = path_config.input_dir / backup_name
            shutil.move(str(target_pdf), str(backup_path))
            logger.info(f"Existing file backed up as: {backup_name}")
        
        shutil.move(str(pdf_path), str(target_pdf))
        logger.info(f"PDF moved back to input: {pdf_path.name}")
        
        # Remove JSON file
        json_path.unlink()
        logger.info(f"JSON file removed: {json_path.name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during reprocessing setup: {e}")
        return False

def main():
    """Main verification function with enhanced workflow."""
    logger.info("Starting enhanced file verification process...")
    
    # Ensure directories exist
    if not path_config.setup_directories():
        logger.error("Failed to setup required directories")
        return
    
    # Find latest files
    latest_json, latest_pdf = find_latest_processed_files()

    if not latest_json:
        logger.info("No files available for verification")
        print("\n📝 No processed files found for verification.")
        return

    if not latest_pdf:
        logger.warning(f"JSON file found but corresponding PDF missing: {latest_json.name}")
        print(f"\n⚠️  Found JSON but missing PDF: {latest_json.name}")
        return

    logger.info(f"Verifying: '{latest_json.name}' against '{latest_pdf.name}'")
    print(f"\n🔍 Verifying: {latest_json.name}")
    print(f"   Against: {latest_pdf.name}")

    # Load JSON data
    try:
        with open(latest_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            logger.error("JSON file is empty")
            print("\n❌ JSON file contains no data")
            return
            
        logger.info(f"Loaded {len(data)} records from JSON")
        
    except Exception as e:
        logger.error(f"Failed to load JSON file '{latest_json.name}': {e}")
        print(f"\n❌ Error loading JSON file: {e}")
        return

    # Run verifications
    print("\n🔍 Running verification checks...")
    
    sequence_findings = verify_article_sequence(data)
    integrity_findings = verify_content_integrity(data, latest_pdf)
    
    all_findings = sequence_findings + integrity_findings

    # Report results
    if not all_findings:
        logger.info("✅ Verification completed successfully - no issues found")
        print("\n✅ VERIFICATION PASSED")
        print("   No critical issues detected in the processed file.")
        return

    # Display findings
    print(f"\n{'='*60}")
    print("⚠️  VERIFICATION ISSUES DETECTED")
    print(f"{'='*60}")
    
    for i, finding in enumerate(all_findings, 1):
        print(f"{i:2d}. {finding}")
        logger.warning(f"Issue {i}: {finding}")
    
    print(f"{'='*60}")
    print(f"Total issues found: {len(all_findings)}")
    
    # Ask user for action
    if interactive_reprocess_decision(latest_pdf, latest_json):
        print("\n🔄 Preparing files for reprocessing...")
        if reprocess_files(latest_pdf, latest_json):
            print("✅ Files prepared for reprocessing")
            print(f"   Run the main processing script to reprocess {latest_pdf.name}")
            logger.info("Files successfully prepared for reprocessing")
        else:
            print("❌ Error preparing files for reprocessing")
    else:
        print("\n📋 Files kept as they are")
        logger.info("User chose to keep files without reprocessing")

if __name__ == "__main__":
    main()
    else:
        print("\n📋 Files kept as they are")
        logger.info("User chose to keep files without reprocessing")

if __name__ == "__main__":
    main()

