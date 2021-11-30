from collections import defaultdict
from typing import Dict, List, Set, Tuple, Union

from corpus.parsers.textparser import TextParser

__SESSION_TYPES__ = ("postgres", "vertica")


def _prepare_terms(
    pairs: List[Tuple[str, Union[str, None]]], collector: set
) -> List[Tuple[List[Tuple[str, int]], Union[List[Tuple[str, int]], None]]]:
    tp = TextParser()
    tok_pairs = []
    for inp, out in pairs:
        inp = tp.tokenize_str(inp)
        collector |= set([tok for tok, _ in inp])

        out = tp.tokenize_str(out) if out else []
        collector |= set([tok for tok, _ in out])
        tok_pairs.append((inp, out))

    return tok_pairs


def query_token_dict(session, token_set: Set[str]) -> Dict[str, int]:
    stmt = "SELECT token, tokenid FROM tokens WHERE "
    stmt += " OR ".join(["token = %s"] * len(token_set))
    cur = session.execute(stmt, tuple(token_set))
    result = dict(cur.fetchall())
    cur.close()
    return result


def get_uris_for(
    examples: List[Tuple[str, Union[str, None]]],
    queries: List[Tuple[str, None]],
    session_type: str,
) -> Dict[str, Tuple[List[int], List[int]]]:
    def _execute_query(session, pairs, token_dict):
        candidates = defaultdict(list)
        for i, pair in enumerate(pairs):
            stmt = _prepare_stmt(*pair)
            with session.execute(stmt, token_dict) as cursor:
                for (key,) in cursor:
                    candidates[key].append(i)
        if pairs:
            print("Example query:")
            print(stmt)
        return candidates

    assert session_type in __SESSION_TYPES__

    if session_type == "vertica":
        from db.VerticaDBSession import VerticaDBSession

        session = VerticaDBSession()
    elif session_type == "postgres":
        from db.PostgresDBSession import PostgresDBSession

        session = PostgresDBSession()
    else:
        return
    token_set = set()
    examples = _prepare_terms(examples, token_set)
    queries = _prepare_terms(queries, token_set)

    token_dict = query_token_dict(session, token_set)

    ex_candidates = _execute_query(session, examples, token_dict)
    q_candidates = _execute_query(session, queries, token_dict)
    return {
        key: (ex_candidates.get(key, []), q_candidates.get(key, []))
        for key in set(ex_candidates.keys()) | set(q_candidates.keys())
    }


def _prepare_stmt(inp: List[Tuple[str, int]], out: Union[List[Tuple[str, int]], None]):
    def _prepare_subquery_stmt(vals):
        stmt = f"SELECT DISTINCT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %({vals[0][0]})s \n"
        for token, idx in vals[1:]:
            stmt += f"AND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %({token})s AND uriid = T0.uriid AND position = T0.position + {idx})"
        return stmt

    stmt = f"SELECT uri FROM uris JOIN ({_prepare_subquery_stmt(inp)}) T USING(uriid)"
    if out:
        stmt += f"\nINTERSECT\nSELECT uri FROM uris JOIN ({_prepare_subquery_stmt(out)}) T USING(uriid)"

    return stmt


if __name__ == "__main__":
    ...
