import logging
from os.path import basename
from urllib.request import urlretrieve

from settings import Settings
from utils import make_dirs


def retrieve(archive_part):
    s = Settings()
    archive_name = basename(archive_part)
    wet_files = s.WET_FILES

    logging.info(f"Retrieve {archive_name}")
    make_dirs(wet_files)
    urlretrieve(s.CC_DOMAIN + archive_part, wet_files + archive_name)
    logging.info(f"Retrieve {archive_name}. Done.")
    return archive_name

