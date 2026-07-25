import logging
import os
from pathlib import Path
import time

from bs4 import BeautifulSoup
import requests

from src.singleton import Singleton
from src.config import Config
from src.util import format_bytes, format_duration

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
        
        self.logger.info(f"{code:<15} Downloading...")
        
        with self.get(
            url = url,
            headers = headers,
            timeout = self.config.timeout,
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
            
            with open(temp_destination, mode) as f:
                for chunk in r.iter_content(self.config.chunk_size):
                    if chunk:
                        f.write(chunk)
        
        time_taken = time.perf_counter() - start_time
        
        if destination.exists():
            temp_destination.unlink()
        
        else:
            temp_destination.rename(destination)
        
        self.logger.info(
            f"{format_bytes(total_size):^10} | {format_duration(time_taken):^10} Downloaded {destination}"
        )
        
        