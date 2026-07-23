import logging

from .args import Args
from .singleton import Singleton
from .enums import HTTPRequestType, HTTPResponseType
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
        
        data = response.data.get("data", [])
        first_match = data[0]
        
        if not isinstance(first_match, dict):
            return None
        
        title = first_match.get("title")
        date = first_match.get("date")
        
        if (
            not title
            or not date
        ):
            return None
        
        return PornDBResponse(title, date)