import logging
import time
from os.path import join

from db.GZIPWriteSession import GZIPWriteSession
from settings import Settings
from stats import Statistics
from utils import open_write, rm_file
from warcio import WARCWriter
from warcio.archiveiterator import ArchiveIterator
from warcio.recordloader import ArcWarcRecord
from warcio.utils import BUFF_SIZE


def main_subroutine(archive_name, s_type="gzip"):
    stat = Statistics.reset(archive_name)
    settings = Settings()
    error_file = None

    UPDATE_EACH = settings.UPDATE_STATS_EACH
    archive_path = join(settings.WET_FILES, archive_name)
    logging.info(f"Started Subroutine on {archive_name}.")

    if s_type == "gzip":
        session = GZIPWriteSession(archive_name=archive_name)

    for i, wet in enumerate(yield_records(archive_path)):
        start_time = time.time()
        url = wet.rec_headers["WARC-Target-URI"]
        stat.max_url_len(len(url))
        try:
            session.insertTerms(wet)
        except Exception as e:
            if error_file is None:
                error_file = open_write(
                    join(settings.ERROR_PATH, archive_name), bytes=True
                )
                error_writer = WARCWriter(error_file)
            stat.add_drop_error((archive_name, i, url))
            error_writer.write_record(wet)
            logging.exception("")
            stat.update_record_retrieval()

        time_diff = time.time() - start_time
        if time_diff > 100:
            logging.warning(
                f"Execution on record ({url}) took more than 10 seconds ({time_diff})"
            )
            if error_file is None:
                error_file = open(join(settings.ERROR_PATH, archive_name), "wb")
                error_writer = WARCWriter(error_file)
            error_writer.write_record(wet)

        if (i + 1) % UPDATE_EACH == 0:
            # logging.info(f"Status: Position {i} of {archive_name}")
            stat.update_record_retrieval()

    session.afterInsert()
    stat.update_record_retrieval()
    rm_file(settings.WET_FILES + archive_name)
    if error_file is not None:
        error_file.close()
    logging.info(f"Finished Subroutine on {archive_name}.")


def yield_records(archive_path: str):
    with open(archive_path, "rb") as wet_file:
        for wet in ArchiveIterator(wet_file):
            if not wet_filter(wet):
                continue

            Statistics().inc_accepted()
            yield wet


def wet_filter(record: ArcWarcRecord) -> bool:
    if record.rec_type != "conversion":
        return False

    identified_language = record.rec_headers.get("WARC-Identified-Content-Language", "")

    # if not identified_language.startswith("eng"):
    if not identified_language == "eng":
        Statistics().inc_drop_lang()
        return False

    return True
