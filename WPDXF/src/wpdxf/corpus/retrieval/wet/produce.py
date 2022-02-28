import logging
from os import path
from urllib.request import urlretrieve

from wpdxf.utils.settings import Settings
from wpdxf.utils.utils import make_dirs


def retrieve(archive_part: str) -> str:
    """Downloads and writes the given archive.

    Args:
        archive_part (str): Archive part as it is in 'warc.paths'.

    Returns:
        str: Archive's filename
    """
    s = Settings()
    archive_name = path.basename(archive_part)
    wet_files = s.WET_FILES

    logging.info(f"Retrieve {archive_name}")

    make_dirs(wet_files)
    urlretrieve(s.CC_DOMAIN + archive_part, path.join(wet_files, archive_name))

    logging.info(f"Retrieve {archive_name}. Done.")
    return archive_name

