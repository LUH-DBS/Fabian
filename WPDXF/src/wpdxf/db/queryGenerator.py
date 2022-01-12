import logging
from collections import defaultdict
from typing import List, Set, Tuple

import psycopg2
from wpdxf.wrapping.objects.pairs import Example, Pair, Query

__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated


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
        self.uriid_dict = {}
        self.unknown_tokens = set()

    def get_uris_for(self, examples: List[Example], queries: List[Query]):
        def remove_unresolved_examples():
            for example in examples.copy():
                if example.tokens() & self.unknown_tokens:
                    examples.remove(example)
            for query in queries.copy():
                if query.tokens() & self.unknown_tokens:
                    queries.remove(query)

        def get_matches(pairs):
            matches = defaultdict(list)
            for pair in pairs:
                for uri in self.query_uris_for_pair(pair):
                    matches[uri].append(pair.id)
            return matches

        self.update_token_dict(examples + queries)
        remove_unresolved_examples()

        example_matches = get_matches(examples)
        query_matches = get_matches(queries)

        keys = set(example_matches) | set(query_matches)
        self.update_uri_dict(keys)
        matches = {}
        for key in keys:
            uri = self.uriid_dict[key]
            matches[uri] = (example_matches[key], query_matches[key])
        return matches

    def update_token_dict(self, pairs: List[Pair]):
        new_tokens = tuple(
            set.union(*(pair.tokens() for pair in pairs)) - set(self.token_dict)
        )
        if not new_tokens:
            return
        stmt = f"SELECT token, tokenid FROM tokens WHERE token IN ({_tuple_interval(new_tokens)})"
        with self.session.execute(stmt, tuple(new_tokens)) as cur:
            self.token_dict.update(dict(cur.fetchall()))
        self.unknown_tokens |= set(new_tokens) - set(self.token_dict)

    def update_uri_dict(self, uriid_set: Set[int]):
        new_uriids = tuple(uriid_set - set(self.uriid_dict))
        if not new_uriids:
            return

        stmt = f"SELECT uriid, uri FROM uris WHERE uriid IN ({_tuple_interval(new_uriids)})"
        with self.session.execute(stmt, new_uriids) as cur:
            self.uriid_dict.update(dict(cur.fetchall()))

    def query_uris_for_pair(self, pair: Pair):
        def query(tokens: List[Tuple[str, int]]):
            if not tokens:
                return set()
                
            interval = ", ".join([f"%({t})s" for t, _ in tokens])
            stmt = f"SELECT tokenid, position, uriid FROM token_uri_mapping WHERE tokenid IN ({interval}) ORDER BY uriid"
            with self.session.execute(stmt, self.token_dict) as cur:
                filtered_result = self.filter_result(cur, tokens)
                # print(cur.query, self.token_dict)
            return filtered_result

        uris = query(pair.tok_inp)
        if isinstance(pair, Example):
            uris &= query(pair.tok_out)

        return uris

    def filter_result(self, cursor, tokens: List[Tuple[str, int]]) -> Set[int]:
        def yield_partition(cursor):
            key = None
            partition = []
            for row in cursor:
                if key is None:  # Initial value
                    key = row[-1]
                    partition.append(row[:-1])
                elif key != row[-1]:  # New partition
                    yield key, partition
                    key = row[-1]
                    partition = [row[:-1]]
                else:  # Same partition
                    partition.append(row[:-1])

        def yield_window(partition: list, window_size: int):
            if len(partition) < window_size:
                return False
            for i in range(len(partition) - window_size + 1):
                yield partition[i : i + window_size]

        def sliding_window_filter(partition: list, tokens: list) -> bool:
            for window in yield_window(partition, len(tokens)):
                w_position_0 = window[0][1]
                if all(
                    window[i] == (tokenid, w_position_0 + offset)
                    for i, (tokenid, offset) in enumerate(tokens)
                ):
                    return True

            return False

        result = set()
        tokens = [(self.token_dict[token], pos) for token, pos in tokens]
        for key, partition in yield_partition(cursor):
            partition.sort(key=lambda x: x[-1])
            if sliding_window_filter(partition, tokens):
                result.add(key)
        return result
