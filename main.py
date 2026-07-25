from src.config import Config
from src.logger import load_logger
from src.javtiful import Javtiful

c = Config()
logger = load_logger(c.debug)

j = Javtiful()
j.run()