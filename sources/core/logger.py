import logging
from colorama import init, Fore, Style

# Colorama initialisieren
init(autoreset=True)

# Neon-Farben
NEON_TURQ = Fore.CYAN + Style.BRIGHT
NEON_ORANGE = Fore.MAGENTA + Style.BRIGHT
NEON_GREEN = Fore.GREEN + Style.BRIGHT
WHITE = Fore.WHITE + Style.NORMAL
RED = Fore.RED + Style.BRIGHT

class FirmwareLogger:
    def __init__(self, log_file="build.log"):
        # Logger Setup
        self.logger = logging.getLogger("FirmwareBuilder")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        # File Handler (reine Textdatei)
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Kurze Aliase für einfachen Call
        self.con = self.console
        self.info = self.info_msg
        self.warn = self.warning
        self.err = self.error

    def console(self, msg):
        print(f"{NEON_TURQ}Console > {NEON_ORANGE}{msg}")
        self.logger.info(f"Console > {msg}")

    def info_msg(self, msg):
        print(f"{NEON_GREEN}Info > {NEON_ORANGE}{msg}")
        self.logger.info(f"Info > {msg}")

    def warning(self, msg):
        print(f"{Fore.YELLOW}Warning > {WHITE}{msg}")
        self.logger.warning(f"Warning > {msg}")

    def error(self, msg):
        print(f"{RED}Error > {NEON_GREEN}{msg}")
        self.logger.error(f"Error > {msg}")
