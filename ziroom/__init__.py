import logging.config
import os
import selectors
import sys
import asyncio
from environs import Env

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ziroom.models import Base

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
isDebug = True if sys.gettrace() else False


def data_path(path):
    return os.path.join(DATA, path)


env = Env()
print("loading environ settings")
env.read_env(path=data_path(".env"))

logging.config.fileConfig(data_path("../logger.cfg"), defaults={"LOG_DIR": data_path("../logs")})
engine = create_engine("sqlite+pysqlite:///" + data_path("all.db"), echo=True, future=True)
Base.metadata.create_all(engine)
session = Session(engine)


# selector = selectors.SelectSelector()
# loop = asyncio.SelectorEventLoop(selector)
# asyncio.set_event_loop(loop)


__all__ = [
    "engine", "session", "env", "data_path", "isDebug"
]
