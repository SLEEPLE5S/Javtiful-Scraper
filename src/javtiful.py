import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import Config
from src.porndb import PornDB
from src.session import Session
from src.enum import Category
from src.util import sanitise_filename


class Javtiful:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = Config()
        self.porndb = PornDB()
        self.session = Session()
    
    def run(self):
        for url in self.config.urls:
            url = self.remove_params(url)
            
            if "/video/" in url:
                self.scrape_video(url)
            
            if "/actress/" in url:
                self.scrape_actress(url)
    
    def scrape_video(
            self,
            url: str,
            actress_name: str | None = None
    ):
        code = self.get_code(url)
        result = self.porndb.search(code)
        
        if not isinstance(result, tuple):
            self.logger.error(f"Failed to get data from {url}")
            return
        
        data, category = result
        data = data.get("data")
        if not isinstance(data, list):
            return
        
        try:
            first_item: dict = data[0]
        
        except IndexError:
            self.logger.warning(f"{code:<10} Failed to find in ThePornDB!")
            return
        
        date = first_item.get("date")
        title = first_item.get("title")
        site: dict = first_item.get("site", {})
        site_name = site.get("name")
        
        if (
            not date
            or not title
            or not site_name
        ):
            return None
        
        # Get download url from page
        page = self.session.get_soup(url)
        if not page:
            self.logger.warning(f"Failed to get page: {url}")
            return
        
        script = page.find("script", {"id": "frontWatchConfig"})
        if not script:
            self.logger.warning(f"Failed to find watch config script in {url}")
            return
        
        try:
            watch_config: dict = json.loads(script.get_text())
        
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to decode watch config from {url}")
            return
        
        sources: list = watch_config.get("playerSources", [])
        try:
            source: dict = sources[0]
        
        except IndexError:
            self.logger.warning(f"Found no player sources in watch config for {url}")
            return
        
        src = str(source.get("src"))
                        
        # Create a path
        match category:
            case Category.JAV:
                base_path = self.config.jav_path
            
            case Category.SCENES:
                base_path = self.config.scene_path
            
            case Category.MOVIES:
                base_path = self.config.movie_path
        
        if code not in title:
            title = f"{code.upper()} {title}"
        
        file_name = Path(sanitise_filename(f"{site_name} {date} {title}"[:240]))
        
        if actress_name:
            file_path = base_path / actress_name / Path(f"{file_name}.mp4")
        
        else:
            file_path = base_path / Path(f"{file_name}.mp4")
        
        self.session.download(src, file_path, code.upper())
    
    def scrape_actress(
            self,
            url: str
    ):
        def get_page_urls(page_num: int) -> list[str]:
            page = self.session.get_soup(url, {"page": str(page_num)})
            if not page:
                self.logger.error(f"Failed to get page {url}?page={page_num}")
                return []
            
            page_urls: list[str] = []
            video_cards = page.select(
                "article.front-video-card:not(.front-partner-card)"
            )
            for video_card in video_cards:
                a = video_card.find("a")
                if not a: continue
                href = a.get("href")
                if not isinstance(href, str): continue
                
                video_url = "https://javtiful.com" + href
                if video_url in video_urls:
                    break
                
                page_urls.append(video_url)
            
            return page_urls
        
        # Get actress name from URL
        end = url.split("/")[-1]
        name = " ".join([v.title() for v in end.split("-")])
        
        # Get absolute last page
        page = self.session.get_soup(url, {"page": "999"})
        if not page:
            self.logger.error(f"Failed to get max page")
            return
        
        # Get max page num from nav
        a = page.find("a", {"class": "front-pagination-link is-active"})
        if not a:
            self.logger.error(f"Failed to find navigation in {url}?page=999")
            return
        try:
            max_page_num = int(a.get_text())
        
        except ValueError:
            self.logger.error(f"Failed to get max page number in {url}?page=999")
            return
        
        # Visit each page to get video links
        video_urls: list[str] = []
        with ThreadPoolExecutor(10, "Page-Thread") as executor:
            futures = {
                executor.submit(get_page_urls, page_num): page_num
                for page_num in range(1, max_page_num + 1)
            }
            
            for future in as_completed(futures):
                page_num = futures[future]
                
                try:
                    page_urls = future.result()
                
                except Exception as e:
                    self.logger.exception(f"{url}: {e}")
                    continue
                
                if not page_urls:
                    self.logger.error(f"Found no urls in {url}?page={page_num}")    
                    return
            
                video_urls.extend(page_urls)
                
        # Remove urls in favour for mosaic
        for video_url in video_urls.copy():
            if "-reducing-mosaic" in video_url:
                without_end = video_url.replace("-reducing-mosaic", "")
                code = self.get_code(without_end)

                if without_end + code in video_urls:
                    video_urls.remove(without_end + code)
                        
        # Download all videos
        with ThreadPoolExecutor(
                self.config.concurrent_downloads,
                "Download-Thread"
        ) as executor:
            futures = {
                executor.submit(
                    self.scrape_video,
                    video_url,
                    name
                ): video_url
                for video_url in video_urls
            }
            
            for future in as_completed(futures):
                video_url = futures[future]
                
                try:
                    future.result()
                
                except Exception as e:
                    self.logger.exception(f"{video_url}: {e}")
                    continue
    
    def get_code(self, url: str) -> str:
        end = url.split("/")[-1]
        if end.endswith("-reducing-mosaic"):
            return end.replace("-reducing-mosaic", "")
        
        return end
    
    def remove_params(self, url: str) -> str:
        parts = urlsplit(url)
        clean_url = urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            "",
            parts.fragment,
        ))
        
        return clean_url