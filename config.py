# config.py

from pathlib import Path
import logging

class PathConfig:
    def __init__(self, base_dir: Path = Path(__file__).parent):
        self.base_dir = base_dir
        self.input_dir = self.base_dir / "input_pdfs"
        self.processed_json_dir = self.base_dir / "processed_json"
        self.processed_pdfs_dir = self.base_dir / "processed_pdfs"
        self.error_dir = self.base_dir / "error_pdfs"
        self.log_file = self.base_dir / "processing.log"
        
        # Processing configuration
        self.max_file_size_mb = 100  # Maximum PDF file size in MB
        self.processing_timeout = 300  # Timeout in seconds
        self.content_similarity_threshold = 0.95  # For verification
        # Feature flags
        self.use_pdfplumber_fallback: bool = True  # Enable dual extraction
        self.max_concurrent_files = 3  # Maximum files to process simultaneously

    def setup_directories(self):
        """Izveido visas nepieciešamās mapes, ja tās neeksistē."""
        try:
            self.input_dir.mkdir(exist_ok=True)
            self.processed_json_dir.mkdir(exist_ok=True)
            self.processed_pdfs_dir.mkdir(exist_ok=True)
            self.error_dir.mkdir(exist_ok=True)
            return True
        except Exception as e:
            logging.error(f"Neizdevās izveidot mapes: {e}")
            return False

    def validate_file(self, file_path: Path) -> tuple[bool, str]:
        """Validate if file can be processed."""
        if not file_path.exists():
            return False, "Fails neeksistē"
        
        if file_path.suffix.lower() != '.pdf':
            return False, "Fails nav PDF formātā"
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return False, f"Fails ir pārāk liels ({file_size_mb:.1f}MB > {self.max_file_size_mb}MB)"
        
        return True, "OK"

path_config = PathConfig()

