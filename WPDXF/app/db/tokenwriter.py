import io
from os.path import join

from corpus.parsers.textparser import TextParser
from utils.settings import Settings
from utils.stats import Statistics
from utils.utils import compress_file, decompress_file
from warcio.recordloader import ArcWarcRecord

DEL = " "


class GZIPTokenWriter:
    """Tokenizes the WET-Record payload into the following delimiter-separated formats:
        (multiple) terms: warc_id{DEL}pos{DEL}token\\n
        (single) mapping: warc_id{DEL}url\\n

        warc_id and URL are both unique for each record.
        warc_id has a standard length of 47 characters, but is not relevant in further steps.
        URL/URI varies in its length and is in many cases longer than 47 characters, 
            but it is highly relevant for grouping results.
        Therefore (warc_id, pos) is used as PK of Terms although (url, pos) would serve the same purpose 
            and makes warc_id irrelevant for further steps.
    """

    CHUNK_SIZE = 1000

    def __init__(self, archive_name):
        self.terms = io.BytesIO()
        self.id_uri_mapping = io.BytesIO()
        self.archive_name = archive_name

    def insertTerms(self, wet: ArcWarcRecord):
        """Parses a given ArcWarcRecord into a structured token representation. 
        Entries are written (appended) to an intermediate buffer.

        Args:
            wet (ArcWarcRecord): (already filtered) WET-Record
        """
        warc_id = wet.rec_headers["WARC-Refers-To"]
        url = wet.rec_headers["WARC-Target-URI"].replace(f"{DEL}", "")

        Statistics().max_url_len(len(url))
        tokens = TextParser().tokenize(wet.content_stream(),)

        for token, pos in tokens:
            # drop0x00 is inserted for compatibility with postgresql.
            # Data retrieved before fix was cleaned with drop0x00 afterwards.
            token = self.drop0x00(token)
            self.terms.write(
                (DEL.join([warc_id, str(pos), token]) + "\n").encode("utf-8")
            )

        self.id_uri_mapping.write((DEL.join([warc_id, url]) + "\n").encode("utf-8"))

    def afterInsert(self):
        """Permanently writes the buffered results into a gzipped file. 
            Usually executed per archive.
            Optionally: Bulk-loads the buffered results directly into a Vertica DB. 
            (Currently not available.)
        """
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

    @staticmethod
    def drop0x00(text: str) -> str:
        """Used for compatibility with postgresql. 
        COPY FROM raises an encoding error when 0x00 occurs in the data.
        As 0x00 does not provide relevant information, it is dropped from tokens.

        Args:
            text (str): 'utf-8' encoded text that might include '0x00' as a character

        Returns:
            str: Clean text without '0x00'.
        """
        return text.replace("\x00", "")
