"""
Colorful Logger Utility for NexuzCore Buildsystem

Usage:
    from core.logger import success, info, warning, error

    success("Console > Busybox wurde erfolgreich installiert!")
    info("Console > Busybox wird gedownloaded, extrahiert und installiert!")
    warning("Console > Etwas ist ungewöhnlich, bitte überprüfen!")
    error("Console > Ein Fehler ist aufgetreten!")
"""

import logging
import sys

# ANSI Farbdefinitionen für "neon"-Farbtöne (anpassbar)
RESET = "\033[0m"
NEON_GREEN = "\033[38;2;57;255;20m"
NEON_CYAN = "\033[38;2;21;255;255m"
NEON_ORANGE = "\033[38;2;255;140;0m"
NEON_RED = "\033[38;2;255;50;40m"

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
        # Unterstützt das custom SUCCESS-Level
        if getattr(record, "success", False):
            fmt = self.FORMATS["SUCCESS"]
        formatter = logging.Formatter(fmt)
        return formatter.format(record)

# Basis-Logger einrichten
logger = logging.getLogger("nexuzcore")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColorFormatter())
logger.handlers = [handler]
logger.propagate = False

# Erfolg als eigenes Level
SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")

def success(msg, *args, **kwargs):
    # Additional kwarg: extra={"success": True} für custom formatting
    logger.log(SUCCESS_LEVEL, msg, *args, extra={"success": True}, **kwargs)

def info(msg, *args, **kwargs):
    logger.info(msg, *args, **kwargs)

def warning(msg, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    logger.error(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)

# OPTIONAL: Standardmäßiges Kommando für print-Ersatz
log = logger