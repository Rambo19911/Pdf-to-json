# config.py

from pathlib import Path

class PathConfig:
    def __init__(self, base_dir: Path = Path(__file__).parent):
        self.base_dir = base_dir
        self.input_dir = self.base_dir / "input_pdfs"
        self.processed_json_dir = self.base_dir / "processed_json"
        self.processed_pdfs_dir = self.base_dir / "processed_pdfs"
        self.error_dir = self.base_dir / "error_pdfs"
        self.log_file = self.base_dir / "processing.log"

    def setup_directories(self):
        """Izveido visas nepieciešamās mapes, ja tās neeksistē."""
        self.input_dir.mkdir(exist_ok=True)
        self.processed_json_dir.mkdir(exist_ok=True)
        self.processed_pdfs_dir.mkdir(exist_ok=True)
        self.error_dir.mkdir(exist_ok=True)

path_config = PathConfig()

