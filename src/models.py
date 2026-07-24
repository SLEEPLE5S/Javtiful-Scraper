from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

from .enums import HTTPRequestType, HTTPResponseType, HTTPStatusCode, PornDBCategory

@dataclass
class HTTPDownloadData:
    time_taken: float
    file_size: int
    destination: Path

@dataclass
class HTTPRequest:
    url: str
    request_type: HTTPRequestType
    response_type: HTTPResponseType
    payload: dict = field(default_factory = dict)
    params: dict[str, str] = field(default_factory = dict)
    headers: dict[str, str] = field(default_factory = dict)

@dataclass
class HTTPResponse:
    url: str
    status_code: HTTPStatusCode
    data: (
        BeautifulSoup 
        | dict 
        | HTTPDownloadData 
        | str
        | None
    ) = None

@dataclass
class Actress:
    name: str
    profile_url: str

@dataclass
class PornDBResponse:
    title: str
    date: str
    poster: str
    category: PornDBCategory