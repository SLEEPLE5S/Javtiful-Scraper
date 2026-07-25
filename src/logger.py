from datetime import datetime
import logging
import sys
import re
import threading
import os


class ConsoleFormatter(logging.Formatter):
    TIME = "\x1b[1;90m"
    LEVEL = "\x1b[34m"
    NAME = "\x1b[35m"
    THREAD = "\x1b[36m"
    BOLD_WHITE = "\x1b[1;37m"
    RESET = "\x1b[0m"

    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        name = record.name
        thread = record.threadName.upper() if record.threadName else ""
        msg = record.getMessage()

        time_str = f"{self.TIME}{time}{self.RESET}"
        level_str = f"{self.LEVEL}{level:<8}{self.RESET}"
        name_str = f"{self.NAME}{name.upper():<20}{self.RESET}"
        thread_str = f"{self.NAME}{thread}{self.RESET}"
        end_str = f" {self.LEVEL}>>{self.RESET}"
        msg_str = re.sub(
            r"\*(.*?)\*",
            lambda m: f"{self.BOLD_WHITE}{m.group(1)}{self.RESET}",
            msg
        )

        return (
            f"{time_str} {level_str} {name_str} {thread_str} {end_str}\n"
            f"      {msg_str}"
        )


class FileHandler(logging.FileHandler):
    def __init__(self, log_dir="logs"):
        os.makedirs(log_dir, exist_ok=True)

        # unique per run
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_file = os.path.join(log_dir, f"{timestamp}.log")

        super().__init__(self.log_file, encoding="utf-8")

        self.latest_file = os.path.join(log_dir, "latest.log")
        self._update_latest()

    def _update_latest(self):
        try:
            with open(self.latest_file, "w", encoding="utf-8") as f:
                f.write(self.log_file)

        except Exception:
            pass


class FileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        level = record.levelname
        name = record.name
        thread = record.threadName or threading.current_thread().name
        msg = record.getMessage()

        return f"{time} {level:<8} {name.upper():<20} {thread.upper():<15} {msg}"


def load_logger(debug = False) -> logging.Logger:
    """Loads the default logging configuration into the code."""
    logger = logging.getLogger()
    
    if debug:
        logger.setLevel(logging.DEBUG)
    
    else:
        logger.setLevel(logging.INFO)

    # Console
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setFormatter(ConsoleFormatter())

    # File
    f_handler = FileHandler()
    f_handler.setFormatter(FileFormatter())

    logging.getLogger("PIL").setLevel(logging.CRITICAL)
    logging.getLogger("URLLIB3").setLevel(logging.CRITICAL)

    logger.handlers.clear()
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    return logger