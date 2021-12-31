from collections import defaultdict
from typing import Dict, List, Set, Tuple

from wrapping.objects.pairs import Example, Pair, Query
from wrapping.tree.filter import TauMatchFilter

__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated

class QueryExecutor:
    def __init__(self, session_type="postgres") -> None:
        assert session_type in __SESSION_TYPES__

        if session_type == "postgres":
            from db.PostgresDBSession import PostgresDBSession

            self.session = PostgresDBSession()
        # elif session_type == "vertica":
        #     from db.VerticaDBSession import VerticaDBSession
        #     session = VerticaDBSession()

        self.token_dict = {}
        self.unknown_tokens = set()

    def update_token_dict(self, pairs: List[Pair]):
        """Prepares the dictionary of named variables used during statement execution.
        Retrieves the token -> token_id mapping for the included tokens.
        Tokens that cannot be found in the DB, are not included in the mapping, but added to the unknown_tokens set.

        Args:
            pairs (List[Pair]): The pairs (examples and queries) of the current execution.
        """
        if not pairs:
            return
        # Union of all tokens, without already cached tokens.
        token_set = set.union(*(pair.tokens() for pair in pairs)) - set(self.token_dict)

        stmt = "SELECT token, tokenid FROM tokens WHERE " + " OR ".join(
            ["token = %s"] * len(token_set)
        )
        with self.session.execute(stmt, tuple(token_set)) as cur:
            self.token_dict.update(dict(cur.fetchall()))
        self.unknown_tokens |= token_set - set(self.token_dict)

    def get_uris_for(
        self, examples: List[Example], queries: List[Query]
    ) -> Dict[str, Tuple[List[int], List[int]]]:

        # Cache tokens
        self.update_token_dict(examples + queries)
        # Prune examples/queries
        for token in self.unknown_tokens:
            for example in examples.copy():
                if token in example.tokens():
                    examples.remove(example)
            for query in queries.copy():
                if token in query.tokens():
                    queries.remove(query)

        example_matches = _execute_query(self.session, examples, self.token_dict)
        query_matches = _execute_query(self.session, queries, self.token_dict)

        matches = {}
        for key in set(example_matches) | set(query_matches):
            matches[key] = (example_matches.get(key, []), query_matches.get(key, []))

        return matches


def _execute_query(
    session, pairs: List[Pair], token_dict: dict,
):
    """Generic Wrapper: Applicable for examples and queries. 
    Generates the statement based on given pairs and
    evaluates the statement against the given DB (session).
    Writes the result into uri -> matches mapping (candidates) based on the specified idx.

    Args:
        session : Database connection (e.g. PostgresDBSession)
        pairs (List[Pair]): List of either examples or queries
        token_dict (dict): token -> token_id mapping
    """
    if not pairs:
        return {}
    stmt = _prepare_stmt(pairs)
    with session.execute(stmt, token_dict) as cur:
        result = dict(cur.fetchall())
        print(cur.query)
    return result


def _prepare_stmt(pairs: List[Pair]) -> str:
    """Returns a uri -> match mapping based on the union of statements for each pair.
    UNION ALL is used, as duplicates are not possible (match is unique for each pair)

    Args:
        pairs (List[Pair]): List of either examples or queries.

    Returns:
        str: The complete statement to evaluate against DB.
    """
    return (
        "SELECT uri, array_agg(match) matches FROM ("
        + " UNION ALL ".join([f"({_prepare_pair_stmt(p)})" for p in pairs])
        + ") U GROUP BY uri"
    )


def _prepare_pair_stmt(pair: Pair) -> str:
    """Returns uri -> match mapping based on the intersection of input and output statements for a single pair.

    Args:
        pair (Pair): Either an example or a query.

    Returns:
        str: Statement for a single pair to evaluate against DB.
    """

    def _prepare_subquery_stmt(vals: List[Tuple[str, int]]):
        # Query for each token list: Find entries in 'token_uri_mapping' that match the first token in the list.
        # Check if the following positions match the other tokens using a semi-join.
        stmt = f"SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %({vals[0][0]})s "
        for token, idx in vals[1:]:
            stmt += (
                "AND EXISTS (SELECT * FROM token_uri_mapping "
                + f"WHERE tokenid = %({token})s "
                + "AND uriid = T0.uriid "
                + f"AND position = T0.position + {idx})"
            )
        return stmt

    inp, out = pair.tok
    stmt = f"SELECT uri, {pair.id} as match FROM uris WHERE uriid IN ({_prepare_subquery_stmt(inp)})"
    if out:
        stmt += f" AND uriid IN ({_prepare_subquery_stmt(out)})"
    return stmt
