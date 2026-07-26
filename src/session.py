from contextlib import nullcontext
import logging
from pathlib import Path
import re
from threading import RLock
import time

from bs4 import BeautifulSoup
import requests
from tqdm import tqdm

from src.singleton import Singleton
from src.config import Config
from src.util import format_bytes, format_duration
from src.logger import ConsoleFormatter

class Session(requests.Session, metaclass = Singleton):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/150.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml"
                ";q=0.9,image/avif,image/webp,image/apng,*/*"
                ";q=0.8"
            )
        })
    
        tqdm.set_lock(RLock())
    
    def get_soup(
            self,
            url: str,
            params: dict[str, str] | None = None,
    ) -> BeautifulSoup | None:
        try:
            r = self.get(
                url = url,
                params = params,
                timeout = self.config.timeout,
            )
        
        except requests.Timeout:
            self.logger.warning(f"{f'[408]':<10} {url}")
            return None
        
        if r.status_code != 200:
            self.logger.warning(f"{f'[{r.status_code}]':<10} {url}")
            return None
        
        try:
            return BeautifulSoup(r.text, "html.parser")
        
        except TypeError:
            self.logger.warning(f"{f'[SOUP]':<10} {url}")
            return None
    
    def get_dict(
            self,
            url: str,
            headers: dict[str, str] | None = None,
            params: dict[str, str] | None = None,
    ) -> dict:
        try:
            r = self.get(
                url = url,
                headers = headers,
                params = params,
                timeout = self.config.timeout,
            )
        
        except requests.Timeout:
            self.logger.warning(f"{f'[408]':<10} {url}")
            return {}
        
        if r.status_code != 200:
            self.logger.warning(f"{f'[{r.status_code}]':<10} {url}")
            return {}
        
        try:
            return r.json()

        except requests.JSONDecodeError:
            self.logger.warning(f"{f'[JSON]':<10} {url}")
            return {}
    
    def download(
            self,
            url: str,
            destination: Path,
            code: str,
    ):
        if destination.exists():
            return None
        
        # For resuming file downloads
        temp_destination = destination.with_suffix(destination.suffix + ".temp")
        
        headers = {}
        downloaded_bytes = 0
        
        if temp_destination.exists():
            downloaded_bytes = temp_destination.stat().st_size
            headers["Range"] = f"bytes={downloaded_bytes}-"
        
        temp_destination.parent.mkdir(parents = True, exist_ok = True)
        start_time = time.perf_counter()
                
        with self.get(
            url = url,
            headers = headers,
            timeout = self.config.timeout,
            stream = True,
        ) as r:
            if r.status_code not in (200, 206):
                self.logger.warning(f"{f'[{r.status_code}]':<10} Failed to download from {url}")
                return None
            
            if downloaded_bytes and r.status_code == 200:
                # Failed resume request
                downloaded_bytes = 0
                temp_destination.unlink(missing_ok = True)
            
            mode = "ab" if downloaded_bytes else "wb"
            total_size = r.headers.get("Content-Length", 0)
            total_size = int(total_size) + downloaded_bytes if total_size else 0
            to_download = int(total_size) - downloaded_bytes if total_size else 0
            
            show_progress = total_size >= 50 * 1024 * 1024

            match = re.match(r"^(.*?)\s+(\d{4}-\d{2}-\d{2})\s+(.*)$", destination.stem)

            if not match:
                return None

            title = match.group(3)
            
            progress_context = (
                tqdm(
                    total=total_size,
                    initial=downloaded_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=f"\x1b[1;36m{code:<.15}\x1b[0m",
                    leave=False,
                    dynamic_ncols=True,
                    ascii="━╸",
                    bar_format=(
                        "{desc}"
                        "\x1b[1;32m{percentage:3.0f}%\x1b[0m "
                        "{bar} "
                        "\x1b[1;37m{n_fmt}\x1b[0m/"
                        "\x1b[1;90m{total_fmt}\x1b[0m "
                        "\x1b[1;90m[{elapsed}<{remaining}]\x1b[0m "
                        "\x1b[1;33m{rate_fmt}\x1b[0m"
                    ),
                    colour="green",
                )
                if show_progress
                else nullcontext()
            )
            
            with progress_context as progress:
                with open(temp_destination, mode) as f:
                    for chunk in r.iter_content(self.config.chunk_size):
                        if chunk:
                            f.write(chunk)
                            
                            if progress:
                                progress.update(len(chunk))
        
        time_taken = time.perf_counter() - start_time
        
        if destination.exists():
            temp_destination.unlink()
        
        else:
            temp_destination.rename(destination)
        
        
        self.log_completion(time_taken, total_size, to_download, destination)
    
    def log_completion(
            self,
            time_taken: float, 
            total_size: int, 
            downloaded: int, 
            destination: Path
    ):
        mbps = (downloaded * 8) / (1024 * 1024) / time_taken
        
        TIME  = "\x1b[1;36m"
        SIZE  = "\x1b[1;33m"
        SPEED = "\x1b[1;32m"
        RESET = "\x1b[0m"
        
        time_str = f"{TIME}{format_duration(time_taken):^10}{RESET}"
        size_str = f"{SIZE}{format_bytes(total_size):^12}{RESET}"
        speed_str = f"{SPEED}{f'{mbps:.2f} Mbps':^15}{RESET}"
        
        tqdm.write(
            f"{time_str} {size_str} {speed_str} {destination.parent.name + "/" + destination.name}"
        )
        