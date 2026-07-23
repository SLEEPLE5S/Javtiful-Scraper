from enum import Enum

class HTTPRequestType(Enum):
    GET = "get"
    POST = "post"
    DOWNLOAD = "download"

class HTTPResponseType(Enum):
    SOUP = "soup"
    TEXT = "text"
    DICT = "dict"

class HTTPStatusCode(Enum):
    OK = 200
    FAIL = 404
    TIMEOUT = 408
    SOUP_FAIL = 409
    DICT_FAIL = 410
    EXISTS_FAIL = 411