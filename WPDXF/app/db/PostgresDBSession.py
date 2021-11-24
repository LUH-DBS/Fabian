import logging
from glob import glob
from os import path

import psycopg2
from utils.settings import Settings
from utils.utils import read_file

VERTICA_CONFIG = Settings().VERTICA_CONFIG
DEL = " "


class PostgresDBSession:
    def __init__(self):
        self._connection = None

    def __del__(self):
        self.close()

    @property
    def connection(self):
        if self._connection is None:
            self._connection = psycopg2.connect(**Settings().POSTGRES_CONFIG)
        return self._connection

    def close(self, commit=True):
        if self._connection is not None:
            if commit:
                self._connection.commit()
            self.connection.close()
            self._connection = None

    @staticmethod
    def probeConnection():
        c = psycopg2.connect(**Settings().POSTGRES_CONFIG)
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
        return cursor.execute(operation, parameters)

    def copy_from(self, limit=0, offset=0):
        terms = sorted(glob(path.join(Settings().TERM_STORE, "*.wet.gz")))
        if offset >= len(terms):
            return []
        u_idx = min(offset + limit, len(terms))
        terms = terms[offset:u_idx]

        for t in terms:
            mapping = path.join(Settings().MAP_STORE, path.basename(t))
            self._copy_from(mapping, t)

    def _copy_from(self, mapping, terms):
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


if __name__ == "__main__":
    c = PostgresDBSession()
    # c.execute_from_file(
    #     "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/vertica/designer_script.sql"
    # )
    c.copy_from(limit=5, offset=1)
    # cur.close()
    c.close()
