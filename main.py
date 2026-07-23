import os

from src.porndb import PornDB
from src.scraper import Scraper
from src.args import Args
from src.logger import load_logger

args = Args()
load_logger(args.debug)

scraper = Scraper()
scraper.scrape()