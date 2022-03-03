from typing import Iterator, List, Set

from wpdxf.wrapping.objects.pairs import Pair

__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated


def _escape_var(variable):
    return f"%({variable})s"


def _tuple_interval(t):
    return ("%s, " * len(t))[:-2]


class QueryExecutor:
    def __init__(self, session_type="postgres") -> None:
        assert session_type in __SESSION_TYPES__

        if session_type == "postgres":
            from wpdxf.db.PostgresDBSession import PostgresDBSession

            self.session = PostgresDBSession()
        # elif session_type == "vertica":
        #     from db.VerticaDBSession import VerticaDBSession
        #     session = VerticaDBSession()

        self.token_dict = {}
        self.unknown_tokens = set()

    def update_token_dict(self, tokens: Set[str]):
        new_tokens = tokens - set(self.token_dict)
        if not new_tokens:
            return
        _interval = _tuple_interval(new_tokens)
        stmt = f"SELECT token, tokenid FROM tokens WHERE token IN ({_interval})"
        with self.session.execute(stmt, tuple(new_tokens)) as cur:
            self.token_dict.update(dict(cur.fetchall()))
        self.unknown_tokens |= new_tokens - set(self.token_dict)
        return self.token_dict, self.unknown_tokens

    def query_pairs(self, pairs: List[Pair]):
        if not pairs:
            return StopIteration

        def remove_unresolved_pairs():
            for pair in pairs.copy():
                if pair.tokens & self.unknown_tokens:
                    pairs.remove(pair)

        all_tokens = set.union(*map(lambda x: x.tokens, pairs))
        self.update_token_dict(all_tokens)
        if self.unknown_tokens:
            remove_unresolved_pairs()
            all_tokens = set.union(*map(lambda x: x.tokens, pairs)) if pairs else set()

        return self.query_single_token_set(all_tokens)

    def query_single_token_set(self, tokenset: Set[str]) -> Iterator:
        if not tokenset:
            return StopIteration
        _where = " OR ".join(f"tokenid = {_escape_var(t)}" for t in tokenset)
        stmt = f"""\
SELECT tokenid, position, uri
FROM (
    SELECT tokenid, position, uriid 
    FROM token_uri_mapping WHERE {_where} 
    ORDER BY uriid, position
) S1 JOIN uris USING(uriid)"""
        with self.session.execute(stmt, self.token_dict) as cur:
            # print("Single Token Query\n", cur.query.decode())
            for item in self.yield_partition(cur):
                yield item

    def query_multi_token_set(self, tokenset: Set[str]) -> Iterator:
        if not tokenset:
            return StopIteration
        _where = " OR ".join(f"tokenid = {_escape_var(t)}" for t in tokenset)
        stmt = f"""\
SELECT tokenid, position, uri
FROM (
    SELECT tokenid, position, uriid, 
        LAG(position) OVER w AS prevpos, 
        LEAD(position) OVER w AS nextpos
    FROM token_uri_mapping
    WHERE {_where}
    WINDOW w AS (PARTITION BY uriid ORDER BY position)
) S JOIN uris USING(uriid)
WHERE prevpos = position - 1
OR nextpos = position + 1
ORDER BY uriid, position"""
        with self.session.execute(stmt, self.token_dict) as cur:
            # print("Multi Token Query\n",cur.query.decode())
            for item in self.yield_partition(cur):
                yield item

    def yield_partition(self, cursor):
        key = None
        partition = []
        for i, row in enumerate(cursor):
            if key is None:  # Initial value
                key = row[-1]
                partition.append(row[:-1])
            elif key != row[-1]:  # New partition
                yield key, partition
                key = row[-1]
                partition = [row[:-1]]
            else:  # Same partition
                partition.append(row[:-1])
        yield key, partition
        print("Total rows:", i)
