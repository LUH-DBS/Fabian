import io
from os.path import join

import vertica_python
from corpus.parsers.textparser import TextParser
from settings import Settings
from stats import Statistics
from utils import compress_file, read_file
from warcio.recordloader import ArcWarcRecord

from db.DBSession import DBSession

DEL = " "


def create_tables():
    stmt = read_file(Settings().BASE_PATH + "vertica/create_tables.sql")
    with vertica_python.connect(**Settings().VERTICA_CONFIG) as c:
        cursor = c.cursor()
        cursor.execute(stmt)
        cursor.close()


def drop_tables():
    with vertica_python.connect(**Settings().VERTICA_CONFIG) as c:
        cursor = c.cursor()
        cursor.execute("DROP TABLE Documents CASCADE")
        cursor.execute("DROP TABLE Terms CASCADE")
        cursor.close()


class GZIPWriteSession(DBSession):
    def __init__(self, archive_name):
        self.terms = io.BytesIO()
        self.id_uri_mapping = io.BytesIO()
        self.archive_name = archive_name

    def insertTerms(self, wet: ArcWarcRecord):
        warc_id = wet.rec_headers["WARC-Refers-To"]
        url = wet.rec_headers["WARC-Target-URI"].replace(f"{DEL}", "")

        Statistics().max_url_len(len(url))
        tokens = TextParser().tokenize(wet.content_stream(),)

        for token, pos in tokens:
            self.terms.write(
                (DEL.join([warc_id, str(pos), token]) + "\n").encode("utf-8")
            )

        self.id_uri_mapping.write((DEL.join([warc_id, url]) + "\n").encode("utf-8"))

    def afterInsert(self):
        path = join(Settings().TERM_STORE, self.archive_name)
        compress_file(path, self.terms)
        path = join(Settings().MAP_STORE, self.archive_name)
        compress_file(path, self.id_uri_mapping)

        # try:
        #     with vertica_python.connect(**VERTICA_CONFIG) as c, c.cursor() as cursor:
        #         stmt = f"COPY Terms(url, position, token) FROM STDIN DELIMITER '{DEL}' ABORT ON ERROR;"
        #         cursor.copy(stmt, self.terms)
        # except:
        #     path = join(Settings().TERM_STORE, self.archive_name)
        #     compress_file(path, self.terms)

        self.terms = io.BytesIO()
        self.id_uri_mapping = io.BytesIO()
