from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .porndb import PornDB
from .util import format_bytes, format_duration
from .args import Args
from .enums import HTTPRequestType, HTTPResponseType, PornDBCategory
from .http_client import HTTPClient
from .models import Actress, HTTPRequest, HTTPResponse, PornDBResponse


class Scraper:
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._args = Args()
        self._http_client = HTTPClient()
        self._porndb = PornDB()
    
    def scrape(self):
        for url in self._args.urls:
            url = self._clean_url(url)
            
            if "/actress/" in url:
                self._handle_actress(url)
            
            if "/video/" in url:
                self._handle_video(url)
    
    def _clean_url(self, url: str) -> str:
        parts = urlsplit(url)
        return urlunsplit(parts._replace(query=""))
    
    def _handle_video(self, url: str, actress: Actress | None = None) -> HTTPResponse | None:
        def get_file_path(search_result: PornDBResponse) -> Path:            
            match search_result.category:
                case PornDBCategory.JAV:
                    path = self._args.jav_path
                
                case PornDBCategory.SCENES:
                    path = self._args.scenes_path
                
                case PornDBCategory.MOVIES:
                    path = self._args.movies_path
                            
            if actress:
                path = path / actress.name

            extension = ".mp4"
            max_filename_length = 230

            filename = f"{search_result.date} {search_result.title}"
            filename = filename[:max_filename_length - len(extension)] + extension

            return path / filename
        
        def get_direct_url(soup: BeautifulSoup) -> str | None:
            video = soup.find("video", {"id": "front-player"})
            if not video: return None
            
            source = video.find("source")
            if not source: return None
            
            return str(source.get("src"))
        
        def get_poster(soup: BeautifulSoup) -> str | None:
            video = soup.find("video", {"id": "front-player"})
            if not video: return None
            
            poster_url = video.get("poster")

            if not isinstance(poster_url, str):
                return None
            
            return "https://javtiful.com" + poster_url
        
        def get_code(url: str) -> str:
            code = url.split("/")[-1]
            parts = code.split("-")[:2]
            
            return "-".join(parts).upper()
            
        
        request = HTTPRequest(
            url = url,
            request_type = HTTPRequestType.GET,
            response_type = HTTPResponseType.SOUP
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return
        
        direct_url = get_direct_url(response.data)
        poster_url = get_poster(response.data)
        code = get_code(url)
        
        if (
            not direct_url
            or not poster_url
        ):
            self._logger.error(f"Failed to extract data from {url}")
            return
        
        # Search for the file name and date using PornDB
        search_result = self._porndb.search(code)
        
        if not search_result:
            self._logger.error(f"{code:<10} Failed to find in PornDB")
            return None
        
        file_path = get_file_path(search_result)
        
        # Download the poster
        if self._args.posters:
            poster_path = file_path.parent / file_path.with_suffix(".jpeg").name
            request = HTTPRequest(
                url = poster_url,
                request_type = HTTPRequestType.DOWNLOAD,
                response_type = HTTPResponseType.DICT,
                payload = {
                    "destination": poster_path
                }
            )
            response = self._http_client.send(request)
        
        # Download the video
        request = HTTPRequest(
            url = direct_url,
            request_type = HTTPRequestType.DOWNLOAD,
            response_type = HTTPResponseType.DICT,
            payload = {
                "destination": file_path
            }
        )
        
        return self._http_client.send(request)
        
    
    def _handle_actress(self, url: str):
        def get_name(soup: BeautifulSoup) -> str | None:
            div = soup.find("div", {"class": "front-actress-detail-head"})
            if not div: return None
            
            h2 = div.find("h2")
            if not h2: return None
            
            return str(h2.get_text())
        
        def get_profile_url(soup: BeautifulSoup) -> str | None:
            div = soup.find("div", {"class": "front-actress-detail-media"})
            if not div: return None
            
            img = div.find("img")
            if not img: return None
            
            return "https://javtiful.com" + str(img.get("src"))
        
        def get_videos_in_page(soup: BeautifulSoup) -> list[str]:
            videos_in_page = []
            
            articles = soup.select(
                "article.front-video-card:not(.front-partner-card)"
            )
            
            for article in articles:
                a = article.find("a")
                if not a: continue
                url = "https://javtiful.com" + str(a.get("href"))
                videos_in_page.append(url)
            
            return videos_in_page
        
        request = HTTPRequest(
            url = url,
            request_type = HTTPRequestType.GET,
            response_type = HTTPResponseType.SOUP
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, BeautifulSoup):
            return
        
        name = get_name(response.data)
        profile_url = get_profile_url(response.data)
        
        if (
            not name
            or not profile_url
        ):
            self._logger.error(f"Failed to get actress data for {url}")
            return
                
        # Get URLs in all pages
        self._logger.info(f"{name:<15} Searching for posts...")
        urls = []
        index = 1
        while True:
            if index != 1:
                request.params["page"] = str(index)
                response = self._http_client.send(request)
            
            if not isinstance(response.data, BeautifulSoup):
                self._logger.error(f"{name:<15} Failed to get page {index}")
                return
            
            videos_in_page = get_videos_in_page(response.data)
            if not videos_in_page: break
            if any(item in videos_in_page for item in urls):
                break
            
            urls.extend(videos_in_page)
            index += 1
        
        # Download all the videos using a thread pool
        actress = Actress(name, profile_url)
        downloads = []

        with ThreadPoolExecutor(
            max_workers = self._args.workers,
            thread_name_prefix = "Actress-Thread"
        ) as executor:
            futures = {
                executor.submit(self._handle_video, video_url, actress): video_url
                for video_url in urls
            }
            
            for future in as_completed(futures.keys()):
                video_url = futures[future]
                
                try:
                    result = future.result()
                
                except Exception as e:
                    self._logger.exception(f"{name:<15} Exception on {video_url}: {e}")
                    continue
                
                if not result: continue
                downloads.append(result)
        
        # Log completion
        total_size = 0
        total_time = 0
        total_files = len(downloads)
        for download in downloads:
            data = download.data
            if not isinstance(data, dict):
                continue
            
            time_taken = data.get("time_taken", 0)
            file_size = data.get("file_size", 0)
            
            total_size += file_size
            total_time += time_taken
        
        self._logger.info(f"{name:<15} {format_bytes(total_size):^10} {format_duration(total_time):^10} Completed {total_files} files")