from contextlib import nullcontext
import logging
from pathlib import Path
from threading import RLock
import time

from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm

from .util import format_bytes, format_duration
from .args import Args
from .enums import HTTPStatusCode, HTTPRequestType, HTTPResponseType
from .models import HTTPRequest, HTTPResponse
from .singleton import Singleton


class HTTPClient(metaclass = Singleton):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._args = Args()
        self._session = requests.Session()
        self._session.headers.update({
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
        
        _adapter = HTTPAdapter(
            pool_connections = self._args.workers * 2,
            pool_maxsize = self._args.workers * 2
        )
        
        self._session.mount("http://", _adapter)
        self._session.mount("https://", _adapter)
        
        tqdm.set_lock(RLock())
    
    def send(self, request: HTTPRequest) -> HTTPResponse:
        try:
            if request.request_type == HTTPRequestType.POST:
                response = self._session.post(
                    url = request.url,
                    json = request.payload,
                    params = request.params,
                    headers = request.headers,
                    timeout = self._args.timeout
                )
            
            elif request.request_type == HTTPRequestType.DOWNLOAD:
                return self._handle_download(request)
            
            else:
                response = self._session.get(
                    url = request.url,
                    params = request.params,
                    headers = request.headers,
                    timeout = self._args.timeout
                )
        
        except requests.exceptions.ConnectTimeout:
            self._logger.warning(f"Connection timed out for {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.TIMEOUT)
        
        if response.status_code != 200:
            self._logger.warning(f"{response.status_code:<10} status error from {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.FAIL)
        
        match request.response_type:
            case HTTPResponseType.SOUP:
                return self._get_soup(request, response)
            
            case HTTPResponseType.TEXT:
                return HTTPResponse(request.url, HTTPStatusCode.OK, response.text)
            
            case HTTPResponseType.DICT:
                return self._get_dict(request, response)
    
    def _get_soup(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        try:
            soup = BeautifulSoup(response.text, "html.parser")
            return HTTPResponse(request.url, HTTPStatusCode.OK, soup)
        
        except TypeError:
            self._logger.warning(f"Failed to convert response to BeautifulSoup in {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.SOUP_FAIL)
    
    def _get_dict(self, request: HTTPRequest, response: requests.Response) -> HTTPResponse:
        try:
            return HTTPResponse(request.url, HTTPStatusCode.OK, response.json())
        
        except requests.exceptions.JSONDecodeError:
            self._logger.warning(f"Failed to convert response to JSON in {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.DICT_FAIL)
    
    def _handle_download(self, request: HTTPRequest) -> HTTPResponse:
        if not request.payload:
            self._logger.critical(f"No payload in download request for: {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.DICT_FAIL)
        
        destination = request.payload.get("destination")
        
        if not isinstance(destination, Path):
            self._logger.critical(f"No destination in payload for download request for {request.url}")
            return HTTPResponse(request.url, HTTPStatusCode.DICT_FAIL)
        
        if destination.exists():
            return HTTPResponse(request.url, HTTPStatusCode.EXISTS_FAIL, {"destination": destination})
        
        temp_destination = destination.with_suffix(destination.suffix + ".temp")
        
        # Handle resume
        headers = {}
        downloaded_bytes = 0
        
        if temp_destination.exists():
            downloaded_bytes = temp_destination.stat().st_size
            headers["Range"] = f"bytes={downloaded_bytes}-"
        
        temp_destination.parent.mkdir(parents = True, exist_ok = True)
        start_time = time.perf_counter()
        
        with self._session.get(
            url = request.url,
            headers = headers,
            timeout = self._args.timeout,
            stream = True
        ) as response:
            if response.status_code not in (200, 206):
                self._logger.warning(f"{response.status_code:<10} Failed download from {request.url}")
                return HTTPResponse(request.url, HTTPStatusCode.FAIL)
            
            if downloaded_bytes and response.status_code == 200:
                # Failed range request
                downloaded_bytes = 0
                temp_destination.unlink(missing_ok = True)
            
            mode = "ab" if downloaded_bytes else "wb"
            total_size = response.headers.get("Content-Length", 0)
            total_size = int(total_size) + downloaded_bytes if total_size else 0
            
            show_progress = total_size >= 50 * 1024 * 1024

            progress_context = (
                tqdm(
                    total = total_size,
                    initial = downloaded_bytes,
                    unit = "B",
                    unit_scale = True,
                    unit_divisor = 1024,
                    desc = f"Downloading {destination.name:<.40}",
                    leave = False,
                    dynamic_ncols = True,
                    ascii = "━╸",
                    bar_format = (
                        "{desc} "
                        "{percentage:3.0f}% {bar} "
                        "{n_fmt}/{total_fmt} "
                        "[{elapsed}<{remaining}, {rate_fmt}]"
                    ),
                    colour = "green"
                )
                if show_progress
                else nullcontext()
            )
            
            with progress_context as progress:
                with open(temp_destination, mode) as f:
                    for chunk in response.iter_content(self._args.chunk_size):
                        if chunk:
                            f.write(chunk)

                            if progress:
                                progress.update(len(chunk))
        
        time_taken = time.perf_counter() - start_time
        file_size = temp_destination.stat().st_size
        temp_destination.rename(destination)
        
        tqdm.write(
            f"{f'{format_bytes(file_size)} | {format_duration(time_taken)}':<20} Downloaded {destination}"
        )
        
        return HTTPResponse(
            request.url,
            HTTPStatusCode.OK,
            data = {
                "destination": destination,
                "time_taken": time_taken,
                "file_size": file_size
            }
        )