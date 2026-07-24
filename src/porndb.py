import logging

from .util import sanitise_string
from .args import Args
from .singleton import Singleton
from .enums import HTTPRequestType, HTTPResponseType, PornDBCategory
from .models import HTTPRequest, PornDBResponse
from .http_client import HTTPClient


class PornDB(metaclass = Singleton):
    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._http_client = HTTPClient()
        self._args = Args()
    
    def search(self, code: str) -> None | PornDBResponse:
        request = HTTPRequest(
            url = "https://api.theporndb.net/jav",
            request_type = HTTPRequestType.GET,
            response_type = HTTPResponseType.DICT,
            params = {
                "external_id": code
            },
            headers = {
                "Authorization": f"Bearer {self._args.porndb_token}"
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return None
        
        data = response.data.get("data", {})
                
        try:
            first_match = data[0]
        
        except IndexError:
            return self._try_scenes(code)
        
        return self._parse_data(first_match, PornDBCategory.JAV)

    def _try_scenes(self, code: str) -> None | PornDBResponse:
        request = HTTPRequest(
            url = "https://api.theporndb.net/scenes",
            request_type = HTTPRequestType.GET,
            response_type = HTTPResponseType.DICT,
            params = {
                "parse": code
            },
            headers = {
                "Authorization": f"Bearer {self._args.porndb_token}"
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return None
        
        data = response.data.get("data", {})
                        
        try:
            first_match = data[0]
        
        except IndexError:
            return self._try_movies(code)
        
        return self._parse_data(first_match, PornDBCategory.SCENES)
    
    def _try_movies(self, code: str) -> None | PornDBResponse:
        request = HTTPRequest(
            url = "https://api.theporndb.net/movies",
            request_type = HTTPRequestType.GET,
            response_type = HTTPResponseType.DICT,
            params = {
                "parse": code
            },
            headers = {
                "Authorization": f"Bearer {self._args.porndb_token}"
            }
        )
        response = self._http_client.send(request)
        
        if not isinstance(response.data, dict):
            return None
        
        data = response.data.get("data", {})
                        
        try:
            first_match = data[0]
        
        except IndexError:
            return None
        
        return self._parse_data(first_match, PornDBCategory.MOVIES)
        
    def _parse_data(self, first_match: dict, category: PornDBCategory) -> PornDBResponse | None:
        title = first_match.get("title")
        date = first_match.get("date")
        
        if (
            not isinstance(title, str)
            or not isinstance(date, str)
        ):
            return None
        
        return PornDBResponse(sanitise_string(title), date.replace(" ", "-"), category)