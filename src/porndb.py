import logging

from src.session import Session
from src.config import Config
from src.singleton import Singleton
from src.enum import Category

class PornDB(metaclass = Singleton):
    def __init__(self):
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.session = Session()
        self.token = self.config.porndb_token
        self.headers = {
            "Authorization": f"Bearer {self.token}"
        }
        self.url = "https://api.theporndb.net"
    
    def search(self, code: str) -> tuple[dict, Category] | None:
        data = self.search_jav(code)        
        if data:
            if data.get("data"):
                return data, Category.JAV
        
        
        data = self.search_scenes(code)
        if data:
            if data.get("data"):
                return data, Category.SCENES
        
        data = self.search_movies(code)
        if data:
            if data.get("data"):
                return data, Category.MOVIES
        
        return None
    
    def search_jav(self, code: str) -> dict | None:
        url = self.url + "/jav"
        param = "external_id"
        r = self.session.get_dict(url, self.headers, {param: code})
    
        if not isinstance(r, dict):
            return None
        
        return r
    
    def search_scenes(self, code: str) -> dict | None:
        url = self.url + "/scenes"
        param = "parse"
        r = self.session.get_dict(url, self.headers, {param: code})
        
        if not isinstance(r, dict):
            return None
        
        return r
    
    def search_movies(self, code: str) -> dict | None:
        url = self.url + "/movies"
        param = "parse"
        r = self.session.get_dict(url, self.headers, {param: code})
        
        if not isinstance(r, dict):
            return None
        
        return r