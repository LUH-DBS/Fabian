from collections import defaultdict
from typing import Dict, List, Set, Tuple

from wrapping.objects.pairs import Example, Pair, Query
from wrapping.tree.filter import TauMatchFilter

__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated


def token_position_expr(pair_id, position, token):
    return f"pos_{pair_id}{position}{token}"


def pair_id_expr(pair_id):
    return f"id_{pair_id}"


def create_token_dict(session, pairs: List[Pair]) -> Dict[str, int]:
    """Prepares the dictionary of named variables used during statement execution.
    Retrieves the token -> token_id mapping for the included tokens.
    The output contains token -> token_id mapping, token -> token_position mapping and pair -> pair_id mapping.
    Tokens that cannot be found in the DB, are not included in the mapping.

    Args:
        session: Database connection (e.g. PostgresDBSession)
        token_set (Set[str]): The set of tokens for which the token_ids are required.

    Returns:
        Dict[str, int]: named variables.
        set: Tokens without a token_id in the DB.
    """
    token_dict = {}
    token_set = set()
    if not pairs:
        return token_dict, token_set
    for pair in pairs:
        token_set |= pair.tokens()

        token_dict.update(
            {
                token_position_expr(pair.id, idx, token): idx
                for token, idx in pair.tok_inp + pair.tok_out
            }
        )
        token_dict[pair_id_expr(pair.id)] = pair.id

    stmt = "SELECT token, tokenid FROM tokens WHERE " + " OR ".join(
        ["token = %s"] * len(token_set)
    )
    with session.execute(stmt, tuple(token_set)) as cur:
        token_dict.update(dict(cur.fetchall()))
    unknown_tokens = token_set - set(token_dict)
    return token_dict, unknown_tokens


def get_uris_for(
    examples: List[Example], queries: List[Query], session_type: str = "postgres",
) -> Dict[str, Tuple[List[int], List[int]]]:
    """Returns a uri-match-mapping (uri -> (example_matches, query_matches)) 
    for each website that contains at least one example or query.

    Args:
        examples (List[Example]): List of input examples.
        queries (List[Query]): List of input queries.
        session_type (str, optional): Specifies the DB type and 
        therefore the DB Connection used for querying. Defaults to "postgres".

    Returns:
        Dict[str, Tuple[List[int], List[int]]]: uri -> matches mapping
    """

    assert session_type in __SESSION_TYPES__

    if session_type == "postgres":
        from db.PostgresDBSession import PostgresDBSession

        session = PostgresDBSession()
    # elif session_type == "vertica":
    #     from db.VerticaDBSession import VerticaDBSession
    #     session = VerticaDBSession()

    token_dict, unknown_tokens = create_token_dict(session, examples + queries)

    # If a token is not existent in the corpus, the whole example/query is not worth to be considered.
    if unknown_tokens:
        for ex in examples.copy():
            if any(tok in ex for tok in unknown_tokens):
                # if any(filter(lambda x: x in ex, unknown_tokens)):
                examples.remove(ex)
        for q in queries.copy():
            if any(tok in q for tok in unknown_tokens):
                queries.remove(q)

    candidates = defaultdict(lambda: ([], []))
    _execute_query(session, examples, token_dict, candidates)
    _execute_query(session, queries, token_dict, candidates)
    return dict(candidates)


def _execute_query(
    session,
    pairs: List[Pair],
    token_dict: dict,
    candidates: defaultdict,
    idx: int = None,
):
    """Generic Wrapper: Applicable for examples and queries. 
    Generates the statement based on given pairs and
    evaluates the statement against the given DB (session).
    Writes the result into uri -> matches mapping (candidates) based on the specified idx.

    Args:
        session : Database connection (e.g. PostgresDBSession)
        pairs (List[Pair]): List of either examples or queries
        token_dict (dict): token -> token_id mapping
        candidates (defaultdict): uri -> matches mapping
        idx (int, optional): Index position inside candidate's matches. 
        Defaults to 1 if List[Query] is passed, 0 oterwise.
    """
    idx = idx or int(isinstance(pairs[0], Query))
    stmt = _prepare_stmt(pairs)
    with session.execute(stmt, token_dict) as cursor:
        for uri, matches in cursor:
            candidates[uri][idx].extend(matches)
        print(cursor.query)


def _prepare_stmt(pairs: List[Pair]) -> str:
    """Returns a uri -> match mapping based on the union of statements for each pair.
    UNION ALL is used, as duplicates are not possible (match is unique for each pair)

    Args:
        pairs (List[Pair]): List of either examples or queries.

    Returns:
        str: The complete statement to evaluate against DB.
    """
    union = "\nUNION ALL\n".join([f"({_prepare_pair_stmt(p)})" for p in pairs])
    return f"SELECT uri, array_agg(match) matches FROM ({union}) U GROUP BY uri"


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
        stmt = f"SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %({vals[0][0]})s \n"
        for token, idx in vals[1:]:
            stmt += (
                "AND EXISTS (SELECT * FROM token_uri_mapping "
                + f"WHERE tokenid = %({token})s "
                + "AND uriid = T0.uriid "
                + f"AND position = T0.position + %({token_position_expr(pair.id, idx, token)})s::integer)"
            )
        return stmt

    inp, out = pair.tok
    stmt = f"SELECT uri, %({pair_id_expr(pair.id)})s as match FROM uris WHERE uriid IN ({_prepare_subquery_stmt(inp)})"
    if out:
        stmt += f" AND uriid IN ({_prepare_subquery_stmt(out)})"
    return stmt
