import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

AUDIT_LOG_FILE = os.path.join(LOG_DIR, 'audit.log')

def setup_logging(gui_queue=None, log_level=logging.INFO, max_bytes=2*1024*1024, backup_count=5):
    """
    Set up centralized logging with rotating file handler, console handler, and optional GUI handler.
    """
    logger = logging.getLogger()
    logger.setLevel(log_level)
    # Remove all handlers first
    while logger.handlers:
        logger.handlers.pop()

    # Rotating file handler
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # GUI handler (if provided)
    if gui_queue is not None:
        class GuiHandler(logging.Handler):
            def emit(self, record):
                msg = self.format(record)
                gui_queue.put({"type": "log", "record": msg})
        gui_handler = GuiHandler()
        gui_handler.setLevel(log_level)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(gui_handler)

    return logger

def log_audit(action, details):
    """
    Log a critical action to the audit log with timestamp, action, and details.
    """
    import datetime
    entry = f"{datetime.datetime.now().isoformat()} | {action} | {details}\n"
    with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(entry) 