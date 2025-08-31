import logging
import sys
from pathlib import Path
from datetime import datetime

from config import BASE_DIR


def setup_logging(log_level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    if log_to_file:
        log_dir = BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_filename = f"swm_scraper_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_dir / log_filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger