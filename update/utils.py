import logging
import os
import datetime

def setup_logger(name, log_file, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s')
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')      
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

app_logger = setup_logger('app_logger', 'app.log', logging.DEBUG)

def ensure_dir(directory_path):
    """Ensures that a directory exists, creating it if necessary."""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            app_logger.info(f"Created directory: {directory_path}")
        except OSError as e:
            app_logger.error(f"Error creating directory {directory_path}: {e}")
            raise # Re-raise to indicate failure at a higher level if needed

def get_session_logfile_name(base_dir, prefix="session"):
    """Generates a unique log file name with a timestamp."""
    # ensure_dir(base_dir) # Called by main.py before this now
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Added microseconds for better uniqueness
    return os.path.join(base_dir, f"{prefix}_{timestamp}.txt") # Changed to .txt for easier opening

def append_to_session_log(session_logfile, content):
    """Appends content to the session log file."""
    try:
        with open(session_logfile, "a", encoding="utf-8") as f:
            f.write(content + "\n")
    except Exception as e:
        # Log to main app logger if session logging fails for a line
        app_logger.error(f"Failed to write to session log '{session_logfile}': {e}")