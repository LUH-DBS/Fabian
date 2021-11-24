import logging
from glob import glob
from os import path

import psycopg2
from utils.settings import Settings
from utils.utils import read_file

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

    def copy_from(self, limit=0, offset=0, *, type):
        if type == 'single':    # Store data as a single Table
            copy = self._copy_from_single
        elif type == 'norm':    # Store data in a normalized form
            copy = self._copy_from_norm
        else:
            return
        terms = sorted(glob(path.join(Settings().TERM_STORE, "*.wet.gz")))
        if offset >= len(terms):
            return []
        u_idx = min(offset + limit, len(terms))
        terms = terms[offset:u_idx]

        for t in terms:
            mapping = path.join(Settings().MAP_STORE, path.basename(t))
            copy(mapping, t)

    def _copy_from_single(self, mapping, terms):
        mapping = f'zcat {mapping} | tr -d "\\0"'
        terms = f'zcat {terms} | tr -d "\\0"'
        print(mapping)
        print(terms)
        cursor = self.connection.cursor()
        cursor.execute("CREATE TEMP TABLE mapping(warc CHAR(47), uri VARCHAR);")
        cursor.execute(
            "CREATE TEMP TABLE terms(warc CHAR(47), position INT, token VARCHAR(200));"
        )
        cursor.execute("COPY mapping FROM PROGRAM %s DELIMITER ' '", (mapping,))
        cursor.execute("COPY terms FROM PROGRAM %s DELIMITER ' '", (terms,))
        cursor.execute(
            "INSERT INTO tok_terms SELECT uri, position, token FROM mapping JOIN terms USING (warc)"
        )
        cursor.execute("DROP TABLE terms;")
        cursor.execute("DROP TABLE mapping;")
        cursor.close()

    def _copy_from_norm(self, mapping, terms):
        mapping = f'zcat {mapping} | tr -d "\\0"'
        terms = f'zcat {terms} | tr -d "\\0"'
        print(mapping)
        print(terms)
        cursor = self.connection.cursor()
        cursor.execute("CREATE TEMP TABLE mapping(warc CHAR(47), uri VARCHAR);")
        cursor.execute(
            "CREATE TEMP TABLE terms(warc CHAR(47), position INT, token VARCHAR(200));"
        )
        cursor.execute("COPY norm_uris(warc, uri) FROM PROGRAM %s DELIMITER ' '", (mapping,))
        cursor.execute("COPY terms FROM PROGRAM %s DELIMITER ' '", (terms,))
        cursor.execute(
            "INSERT INTO norm_terms SELECT uriid, position, token FROM norm_uris JOIN terms USING (warc)"
        )
        cursor.execute("DROP TABLE terms;")
        cursor.close()


if __name__ == "__main__":
    c = PostgresDBSession()
    # c.execute_from_file(
    #     "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/vertica/designer_script.sql"
    # )
    c.copy_from(limit=5, offset=1)
    # cur.close()
    c.close()
