import logging
import sys
import os

# ANSI Farbdefinitionen
RESET = "\033[0m"
NEON_GREEN = "\033[38;2;57;255;20m"
NEON_CYAN = "\033[38;2;21;255;255m"
NEON_ORANGE = "\033[38;2;255;140;0m"
NEON_RED = "\033[38;2;255;50;40m"

# Custom Formatter für Konsole
class ColorFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: f"{NEON_CYAN}[debug]{RESET} | %(message)s",
        logging.INFO:  f"{NEON_CYAN}[info]{RESET} | %(message)s",
        logging.WARNING: f"{NEON_ORANGE}[warning]{RESET} | %(message)s",
        logging.ERROR: f"{NEON_RED}[error]{RESET} | %(message)s",
        logging.CRITICAL: f"{NEON_RED}[critical]{RESET} | %(message)s",
        "SUCCESS": f"{NEON_GREEN}[success]{RESET} | %(message)s"
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self.FORMATS.get(record.levelname, self.FORMATS[logging.INFO]))
        if getattr(record, "success", False):
            fmt = self.FORMATS["SUCCESS"]
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

# Formatter ohne Farben für Datei
class PlainFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG: "[debug] | %(message)s",
        logging.INFO: "[info] | %(message)s",
        logging.WARNING: "[warning] | %(message)s",
        logging.ERROR: "[error] | %(message)s",
        logging.CRITICAL: "[critical] | %(message)s",
        "SUCCESS": "[success] | %(message)s"
    }

    def format(self, record):
        fmt = self.FORMATS.get(record.levelno, self.FORMATS.get(record.levelname, self.FORMATS[logging.INFO]))
        if getattr(record, "success", False):
            fmt = self.FORMATS["SUCCESS"]
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

# Basis-Logger einrichten
logger = logging.getLogger("nexuzcore")
logger.setLevel(logging.DEBUG)

# Konsolen-Handler (bunt)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ColorFormatter())

# Datei-Handler (ohne Farben)
logfile_path = os.path.join(os.getcwd(), "nexuzcore-build.log")
file_handler = logging.FileHandler(logfile_path, encoding='utf-8')
file_handler.setFormatter(PlainFormatter())

logger.handlers = [console_handler, file_handler]
logger.propagate = False

# Erfolg als eigenes Level
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

def success(msg, *args, **kwargs):
    logger.log(SUCCESS_LEVEL, msg, *args, extra={"success": True}, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

# Für direkten Zugriff
log = logger