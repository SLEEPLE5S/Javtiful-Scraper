import os
from pathlib import Path
from dotenv import load_dotenv
from argparse import ArgumentParser, Namespace

from src.singleton import Singleton

class Config(metaclass = Singleton):
    def __init__(self):
        # From env
        load_dotenv()
        
        self.porndb_token = os.getenv("TPDB_TOKEN")
        
        # Args
        args = self.parse_args()
        
        self.urls: list[str] = args.urls
        self.jav_path: Path = Path(args.jav_path)
        self.scene_path: Path = Path(args.scene_path)
        self.movie_path: Path = Path(args.movie_path)
        self.debug = args.debug
        self.concurrent_downloads: int = args.concurrent_downloads
        self.timeout: int = args.timeout
        self.chunk_size: int = args.chunk_size

    def parse_args(self) -> Namespace:
        p = ArgumentParser()
        
        p.add_argument(
            "urls",
            nargs = "+",
            metavar = "URLs",
            help = "Javtiful URLs",
        )
        
        p.add_argument(
            "--timeout",
            type = int,
            default = 10,
            help = "Amount of time of inactivity before a request times out.",
        )
        
        p.add_argument(
            "--chunk-size",
            type = int,
            default = 1024 * 1024,
            help = "Amount of chunks to download in one request.",
        )
        
        p.add_argument(
            "--debug",
            action = "store_true",
            help = "Enable debug logging.",
        )
        
        p.add_argument(
            "--jav-path",
            type = str,
            default = "./Downloads/Jav",
            help = "Path to download Jav files.",
        )
        
        p.add_argument(
            "--scene-path",
            type = str,
            default = "./Downloads/Scenes",
            help = "Path to scene files.",
        )
        
        p.add_argument(
            "--movie-path",
            type = str,
            default = "./Downloads/Movies",
            help = "Path to download movie files.",
        )
        
        p.add_argument(
            "--concurrent-downloads",
            type = int,
            default = 2,
            help = "Amount of downloads to happen at once.",
        )
        
        return p.parse_args()