from argparse import ArgumentParser, Namespace
from pathlib import Path

import os
from dotenv import load_dotenv

from .singleton import Singleton

class Args(ArgumentParser, metaclass = Singleton):
    def __init__(self):
        super().__init__()
        _args = self._parse()
        
        self.urls: list[str] = _args.urls
        self.download_path = Path(_args.download_path)
        self.chunk_size: int = _args.chunk_size
        self.debug: bool = _args.debug
        self.timeout: int = _args.timeout
        self.posters: bool = _args.posters
        self.profile: bool = _args.profile
        self.workers: int = _args.workers
        
        load_dotenv(".env")
        self.porndb_token = os.getenv("TPDB_TOKEN")
    
    def _parse(self) -> Namespace:
        self.add_argument(
            "urls",
            nargs = "+",
            metavar = "URLs",
            help = "Javtiful URLs."
        )
        
        self.add_argument(
            "--download-path",
            type = str,
            default = "./Downloads",
            help = "Directory to download files to."
        )
        
        self.add_argument(
            "-cs", "--chunk_size",
            type = int,
            default = 1024 * 1024,
            help = "Amount of bytes to download per chunk."
        )
        
        self.add_argument(
            "--debug",
            action = "store_true",
            help = "Enable debug logging."
        )
        
        self.add_argument(
            "--timeout",
            type = int,
            default = 10,
            help = "Amount of time in seconds to timeout a HTTP request."
        )
        
        self.add_argument(
            "--posters",
            action = "store_true",
            help = "Whether to download posters alongside the video."
        )
        
        self.add_argument(
            "--profile",
            action = "store_true",
            help = "Whether to download the profile image of the actress when downloading actresses."
        )
        
        self.add_argument(
            "--workers",
            type = int,
            default = 10,
            help = "Amount of concurrent downloads with actress downloading."
        )
        
        return self.parse_args()
    
    