import logging
import os
import re
from datetime import datetime

class SensitiveDataFilter(logging.Filter):
    """
    Filter to mask sensitive data like IP addresses and emails in logs.
    """
    def filter(self, record):
        if isinstance(record.msg, str):
            # Mask IPv4 addresses (e.g., 192.168.1.1 -> 192.168.1.***)
            record.msg = re.sub(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b', r'\1***', record.msg)
            
            # Mask Email addresses (e.g., user@domain.com -> u***@domain.com)
            record.msg = re.sub(r'\b([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', r'\1***@\2', record.msg)
            
            # Mask potential API Keys / Secrets in strings (e.g., AIza... -> AIza***)
            record.msg = re.sub(r'(AIza[a-zA-Z0-9_-]{4})[a-zA-Z0-9_-]+', r'\1***', record.msg)
        return True

def setup_logging():
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.getcwd(), "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Log filename with date
    log_file = os.path.join(log_dir, f"security_orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger("SecurityOrchestrator")
    logger.addFilter(SensitiveDataFilter())

    return logger

# Initialize central logger
logger = setup_logging()
