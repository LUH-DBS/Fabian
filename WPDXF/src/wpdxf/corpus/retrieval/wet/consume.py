import logging
import time
from os.path import join

from warcio import WARCWriter
from warcio.archiveiterator import ArchiveIterator
from warcio.recordloader import ArcWarcRecord
from wpdxf.db.tokenwriter import GZIPTokenWriter
from wpdxf.utils.settings import Settings
from wpdxf.utils.stats import Statistics
from wpdxf.utils.utils import open_write, rm_file



def main_subroutine(archive_name: str):
    """This is the routine to be executed on each individual WET-archive.
    It iterates over the archive's records, filters for the relevant subset
    and writes the tokenized records into files 
    (which can be bulk-loaded into Vertica via COPY).

    Args:
        archive_name (str): The archive's filename without a path specification.
            E.g.: CC-MAIN-20211015192439-20211015222439-00000.warc.wet.gz
    """
    stat = Statistics.reset(archive_name)
    settings = Settings()
    error_file = None
    error_writer = None

    UPDATE_EACH = settings.UPDATE_STATS_EACH
    archive_path = join(settings.WET_FILES, archive_name)
    logging.info(f"Started Subroutine on {archive_name}.")

    session = GZIPTokenWriter(archive_name=archive_name)

    for i, wet in enumerate(yield_records(archive_path)):
        url = wet.rec_headers["WARC-Target-URI"]
        stat.max_url_len(len(url))

        start_time = time.time()

        try:
            # tokenize and store wet payload
            session.insertTerms(wet)

        except Exception:
            # Log any type of exception for later investigation
            error_file = error_file or open_write(
                join(settings.ERROR_PATH, archive_name), bytes=True
            )
            error_writer = error_writer or WARCWriter(error_file)
            error_writer.write_record(wet)

            logging.exception("")

            stat.add_drop_error((archive_name, i, url))
            stat.update_record_retrieval()

        time_diff = time.time() - start_time
        if time_diff > 100:
            # Log records that took more than 100 seconds for processing
            # Not that relevant, but interesting to see and good for
            # analysing and boosting the performance.
            error_file = error_file or open_write(
                join(settings.ERROR_PATH, archive_name), bytes=True
            )
            error_writer = error_writer or WARCWriter(error_file)
            error_writer.write_record(wet)

            logging.warning(
                f"Execution on record ({url}) took more than 10 seconds ({time_diff})"
            )

        if (i + 1) % UPDATE_EACH == 0:
            # logging.info(f"Status: Position {i} of {archive_name}")
            stat.update_record_retrieval()

    # write results to file
    session.afterInsert()
    # write statistics to file
    stat.update_record_retrieval()
    # remove raw WET-file
    rm_file(settings.WET_FILES + archive_name)
    if error_file is not None:
        error_file.close()

    logging.info(f"Finished Subroutine on {archive_name}.")


def yield_records(archive_path: str) -> ArcWarcRecord:
    """Iterates and filters an archive located at 'archive_path'
       with warcio.archiveiterator.ArchiveIterator.

    Args:
        archive_path (str): Archive's absolute location

    Yields:
        ArcWarcRecord: The next valid record in the current archive.
    """
    with open(archive_path, "rb") as wet_file:
        for wet in filter(wet_filter, ArchiveIterator(wet_file)):
            yield wet


def wet_filter(record: ArcWarcRecord) -> bool:
    """WET-Record filter. A record is considered as valid if:
    1) Its record type is 'conversion' (no 'warcinfo', ...)
    2) Its identified language is only english (no 'ger', but also no 'eng, ger')
    Statistics regarding amounts of dropped/accepted records are automatically updated.

    Args:
        record (ArcWarcRecord): A single ArcWarcRecord

    Returns:
        bool: Record is valid or not.
    """
    if record.rec_type != "conversion":
        return False

    identified_language = record.rec_headers.get("WARC-Identified-Content-Language", "")

    # if not identified_language.startswith("eng"):
    if not identified_language == "eng":
        Statistics().inc_drop_lang()
        return False

    Statistics().inc_accepted()
    return True
