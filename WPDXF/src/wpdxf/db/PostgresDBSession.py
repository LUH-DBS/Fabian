import logging
import random
from glob import glob
from os import path

random.seed(0)

import psycopg2
from wpdxf.utils.settings import Settings
from wpdxf.utils.utils import read_file

POSTGRES_CONFIG = Settings().POSTGRES_CONFIG
DEL = " "


class PostgresDBSession:
    def __init__(self):
        self._connection = None

    def __del__(self):
        self.close()

    @property
    def connection(self):
        if self._connection is None:
            self._connection = psycopg2.connect(**POSTGRES_CONFIG)
        return self._connection

    def close(self, commit=True):
        if self._connection is not None:
            if commit:
                self._connection.commit()
            self.connection.close()
            self._connection = None

    @staticmethod
    def probeConnection():
        c = psycopg2.connect(**POSTGRES_CONFIG)
        c.close()

    def execute_from_file(self, filename):
        cursor = self.connection.cursor()

        stmts = read_file(filename)
        while stmts:
            stmt, _, stmts = stmts.partition(";")
            if not stmt.startswith("--"):
                self.execute(stmt, cursor=cursor)
        cursor.close()

    def execute(self, operation, parameters=None, cursor=None):
        cursor = cursor or self.connection.cursor()
        cursor.execute(operation, parameters)
        return cursor

    def copy_from(self, limit=0, offset=0):
        terms = sorted(glob(path.join(Settings().TERM_STORE, "*.wet.gz")))
        if offset >= len(terms):
            return []
        u_idx = min(offset + limit, len(terms))
        self._copy_iter(terms[offset:u_idx])

    def copy_from_sample(self, limit):
        terms = sorted(glob(path.join(Settings().TERM_STORE, "*.wet.gz")))
        self._copy_iter(random.sample(terms, k=limit))

    def _copy_iter(self, terms):
        for t in terms:
            bname = path.basename(t)
            mapping = path.join(Settings().MAP_STORE, bname)

            logging.info(f"Started: Copy {bname} into Postgres DB.")
            self._copy_from(mapping, t)
            logging.info(f"Finished: Copy {bname} into Postgres DB.")

    def _copy_from(self, mapping, terms):
        mapping = f'zcat {mapping} | tr -d "\\0"'
        terms = f'zcat {terms} | tr -d "\\0"'

        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS uris(uriid SERIAL PRIMARY KEY, uri VARCHAR)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS tokens(token VARCHAR(200) PRIMARY KEY, tokenid SERIAL)"
        )
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS token_uri_mapping(uriid INT, position INT, tokenid INT);"
        )

        cursor.execute("DROP TABLE IF EXISTS cp_tokens;")
        cursor.execute("DROP TABLE IF EXISTS cp_uris;")

        cursor.execute(
            "CREATE TEMP TABLE cp_tokens(warc CHAR(47), position INT, token VARCHAR(200));"
        )
        cursor.execute("CREATE TEMP TABLE cp_uris(warc CHAR(47), uri VARCHAR);")

        cursor.execute("COPY cp_tokens FROM PROGRAM %s DELIMITER ' ';", (terms,))
        cursor.execute("COPY cp_uris FROM PROGRAM %s DELIMITER ' ';", (mapping,))

        cursor.execute(
            "INSERT INTO tokens(token) SELECT DISTINCT token FROM cp_tokens ON CONFLICT DO NOTHING;"
        )
        cursor.execute(
            """ WITH 
                    this_uris(uriid, uri) AS
                        (INSERT INTO uris(uri) SELECT uri FROM cp_uris RETURNING *)

                INSERT INTO token_uri_mapping 
                    SELECT uriid, position, tokenid 
                    FROM this_uris 
                        JOIN cp_uris USING(uri) 
                        JOIN cp_tokens USING(warc) 
                        JOIN tokens USING(token)
            """
        )
        cursor.execute("DROP TABLE cp_tokens;")
        cursor.execute("DROP TABLE cp_uris;")

    def delete_entries_for_uri(self, uri):
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM uris WHERE uri = %s RETURNING uriid", (uri,))
        # As uri is unique, this for-loop should iterate over a single uriid.
        for uriid in cursor.fetchall():
            cursor.execute("DELETE FROM token_uri_mapping WHERE uriid = %s", uriid)
        cursor.close()