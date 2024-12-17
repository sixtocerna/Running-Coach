import logging

def setup_logger(log_file: str, level=logging.INFO):
    """
    Set up a logger that writes to a file and prints to the console.
    
    :param log_file: File path for the log file
    :param level: Logging level (e.g., logging.INFO, logging.DEBUG)
    :return: Configured logger
    """
    logger = logging.getLogger()  # Use the root logger
    logger.setLevel(level)

    # Check if handlers already exist (to prevent duplicates)
    if not logger.handlers:
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def speed_to_pace(speed_mps):
    
    pace_minutes = 16.666666667 / speed_mps

    minutes = int(pace_minutes)
    seconds = int((pace_minutes - minutes) * 60)

    return f"{minutes}:{seconds:02d}min/km"



