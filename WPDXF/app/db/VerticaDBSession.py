import logging
from glob import glob
from os import path

import vertica_python
from utils.settings import Settings
from utils.utils import read_file

VERTICA_CONFIG = Settings().VERTICA_CONFIG
DEL = " "

"""
This class is DEPRECATED!
As Postgres is used to handle the DB, this early Vertica connection is no longer developed.
"""
class VerticaDBSession:
    def __init__(self):
        self._connection = None

    def __del__(self):
        self.close()

    @property
    def connection(self) -> vertica_python.Connection:
        if self._connection is None:
            self._connection = vertica_python.connect(**Settings().VERTICA_CONFIG)
        return self._connection

    def close(self, commit=True):
        if self._connection is not None:
            if commit:
                self._connection.commit()
            self.connection.close()
            self._connection = None

    @staticmethod
    def probeConnection():
        c = vertica_python.connect(**Settings().VERTICA_CONFIG)
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
        try:
            return cursor.execute(operation, parameters)
        except vertica_python.errors.QueryError:
            logging.exception("")

    def copy_from(self, limit=0, offset=0):
        terms = sorted(glob(path.join(Settings().TERM_STORE, "*.wet.gz")))
        if offset >= len(terms):
            return []
        u_idx = min(offset + limit, len(terms))
        terms = terms[offset:u_idx]

        mapping = [
            "/home/vertica/data/store/mapping/" + path.basename(t) for t in terms
        ]
        #mapping = [path.join(Settings().MAP_STORE, path.basename(t)) for t in terms]
        terms = ["/home/vertica/data/store/terms/" + path.basename(t) for t in terms]
        # TODO: This is  only necessary for local tests as paths differ, remove before execution on the server

        mapping = ", ".join(map(lambda term: f"'{term}'", mapping))
        terms = ", ".join(map(lambda term: f"'{term}'", terms))

        self._copy_from(mapping, terms)

    def _copy_from(self, mapping, terms):
        print(mapping)
        print(terms)
        cursor = self.connection.cursor()
        cursor.execute(
            "COPY wpdxf.mapping FROM :mapping GZIP delimiter ' ' ABORT ON ERROR;",
            {"mapping": mapping},
        )
        cursor.execute(
            "COPY wpdxf.terms FROM :terms GZIP delimiter ' ' ABORT ON ERROR;",
            {"terms": terms},
        )
        cursor.close()


if __name__ == "__main__":
    c = VerticaDBSession()
    # c.execute_from_file(
    #     "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/vertica/designer_script.sql"
    # )
    cur = c.execute("SELECT * FROM wpdxf.mapping;")
    c.copy_from(limit=1, offset=0)
    cur.close()
    c.close()
