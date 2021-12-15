from collections import defaultdict
from typing import Dict, List, Set, Tuple

from wrapping.objects.pairs import Example, Pair, Query
from wrapping.tree.filter import TauMatchFilter

__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated


def query_token_dict(session, token_set: Set[str]) -> Dict[str, int]:
    stmt = "SELECT token, tokenid FROM tokens WHERE "
    stmt += " OR ".join(["token = %s"] * len(token_set))
    cur = session.execute(stmt, tuple(token_set))
    result = dict(cur.fetchall())
    cur.close()
    return result


def get_uris_for(
    examples: List[Example], queries: List[Query], session_type: str = "postgres",
) -> Dict[str, Tuple[List[int], List[int]]]:
    def _execute_query(
        session, pairs: List[Pair], token_dict: dict, candidates: defaultdict, idx: int
    ):
        stmt = _prepare_stmt(pairs)
        with session.execute(stmt, token_dict) as cursor:
            for uri, matches in cursor:
                candidates[uri][idx].extend(matches)

    assert session_type in __SESSION_TYPES__

    if session_type == "postgres":
        from db.PostgresDBSession import PostgresDBSession

        session = PostgresDBSession()
    # elif session_type == "vertica":
    #     from db.VerticaDBSession import VerticaDBSession
    #     session = VerticaDBSession()

    token_set = set()
    for pair in examples + queries:
        token_set |= pair.tokens()

    token_dict = query_token_dict(session, token_set)
    # If a token is not existent in the corpus, the whole example/query is not worth to be considered.
    unknown_tokens = token_set - set(token_dict)
    if unknown_tokens:
        for ex in examples.copy():
            if any(filter(lambda x: x in ex, unknown_tokens)):
                examples.remove(ex)
        for q in queries.copy():
            if any(filter(lambda x: x in q, unknown_tokens)):
                queries.remove(q)

    candidates = defaultdict(lambda: ([], []))
    _execute_query(session, examples, token_dict, candidates, 0)
    _execute_query(session, queries, token_dict, candidates, 1)
    return dict(candidates)


def _prepare_stmt(pairs: List[Pair]):
    union = "\nUNION ALL\n".join([f"({_prepare_pair_stmt(p)})" for p in pairs])
    return f"SELECT uri, array_agg(match) matches FROM ({union}) U GROUP BY uri"


def _prepare_pair_stmt(pair: Pair):
    def _prepare_subquery_stmt(vals):
        stmt = f"SELECT DISTINCT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %({vals[0][0]})s \n"
        for token, idx in vals[1:]:
            stmt += f"AND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %({token})s AND uriid = T0.uriid AND position = T0.position + {idx})"
        return stmt

    inp, out = pair.tok
    stmt = f"SELECT uri, {pair.id} as match FROM uris JOIN ({_prepare_subquery_stmt(inp)}) T USING(uriid)"
    if out:
        stmt += f"\nINTERSECT\nSELECT uri, {pair.id} as match FROM uris JOIN ({_prepare_subquery_stmt(out)}) T USING(uriid)"
    return stmt


if __name__ == "__main__":
    res_filter = TauMatchFilter(2)
    examples = [
        Example(i, *vals)
        for i, vals in enumerate(
            [
                ("Reader rescue", "OutB"),
                ("Rumours of talks with Carlsberg cheer S&N", "Robert Lindsay"),
            ]
        )
    ]
    queries = [
        Query(i, *vals) for i, vals in enumerate([("Something to shout about", None)])
    ]
    print(get_uris_for(examples, queries, res_filter))
    print(examples)
