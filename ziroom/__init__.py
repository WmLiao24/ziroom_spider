import logging.config
import os
import sys
from configparser import ConfigParser

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ziroom.models import Base

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
isDebug = True if sys.gettrace() else False


def data_path(path):
    return os.path.join(DATA, path)


other_config = ConfigParser()
if os.path.exists(data_path("other.cfg")):
    print("loading other config.")
    with open(data_path("other.cfg"), "r", encoding="utf8") as f:
        other_config.read_file(f)

logging.config.fileConfig(data_path("../logger.cfg"), defaults={"LOG_DIR": data_path("../logs")})
engine = create_engine("sqlite+pysqlite:///" + data_path("all.db"), echo=True, future=True)
Base.metadata.create_all(engine)
session = Session(engine)


__all__ = [
    "engine", "session", "other_config", "data_path", "isDebug"
]
