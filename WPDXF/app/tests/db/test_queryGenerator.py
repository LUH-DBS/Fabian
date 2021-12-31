from wrapping.objects.pairs import Example, Query

from db.queryGenerator import QueryExecutor, _prepare_pair_stmt, _prepare_stmt


class TestDBSession:
    class CloseableTuple:
        def __init__(self, data) -> None:
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            ...

        def fetchall(self):
            return self.data

    last_stmt = None
    last_args = None
    func = None

    def execute(self, stmt, args):
        self.last_stmt = stmt
        return TestDBSession.CloseableTuple(self.func(args))


def test_create_token_dict():
    examples = [Example(0, "0", "1")]
    queries = [Query(1, "2"), Query(2, "3 4")]

    session = TestDBSession()
    session.func = lambda args: ((str(t), int(t)) for t in sorted(args))

    query_executor = QueryExecutor()
    query_executor.session = session

    input = (examples,)
    target = (
        {"0": 0, "1": 1,},  # token -> token_id
        set(),
    )
    target_stmt = "SELECT token, tokenid FROM tokens WHERE token = %s OR token = %s"

    query_executor.update_token_dict(*input)
    assert target == (query_executor.token_dict, query_executor.unknown_tokens)
    assert session.last_stmt == target_stmt

    input = (queries,)
    target = (
        {"0": 0, "1": 1, "2": 2, "3": 3, "4": 4},  # token -> token_id
        set(),
    )
    target_stmt = (
        "SELECT token, tokenid FROM tokens WHERE token = %s OR token = %s OR token = %s"
    )

    query_executor.update_token_dict(*input)
    assert target == (query_executor.token_dict, query_executor.unknown_tokens)
    assert session.last_stmt == target_stmt

    # Check behavior on empty token_set
    query_executor = QueryExecutor()
    query_executor.session = session
    session.func = lambda args: (("A", 0),)
    input = (set(),)
    target = ({}, set())
    query_executor.update_token_dict(*input)
    assert target == (query_executor.token_dict, query_executor.unknown_tokens)

    # Check behavior on missing token_ids
    query_executor = QueryExecutor()
    query_executor.session = session
    session.func = lambda args: (
        (t, i) for i, t in enumerate(sorted(args)) if i % 2 == 0
    )

    input = (examples + queries,)
    target = (
        {"0": 0, "2": 2, "4": 4,},  # token -> token_id
        set(("1", "3")),
    )
    target_stmt = "SELECT token, tokenid FROM tokens WHERE token = %s OR token = %s OR token = %s OR token = %s OR token = %s"

    query_executor.update_token_dict(*input)
    assert target == (query_executor.token_dict, query_executor.unknown_tokens)
    assert session.last_stmt == target_stmt


def test_prepare_query():
    examples = [Example(0, "This is an example input.", "This is an example output.")]
    queries = [Query(1, "This is an example query.")]

    input = examples[0]
    target_pair_ex = "SELECT uri, 0 as match FROM uris WHERE uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s AND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(input)s AND uriid = T0.uriid AND position = T0.position + 1)) AND uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s AND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(output)s AND uriid = T0.uriid AND position = T0.position + 1))"

    output = _prepare_pair_stmt(input)
    assert target_pair_ex == output

    input = examples
    target = (
        "SELECT uri, array_agg(match) matches FROM (("
        + target_pair_ex
        + ")) U GROUP BY uri"
    )
    output = _prepare_stmt(input)
    assert target == output

    input = queries[0]
    target_pair_q = "SELECT uri, 1 as match FROM uris WHERE uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s AND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(query)s AND uriid = T0.uriid AND position = T0.position + 1))"

    output = _prepare_pair_stmt(input)
    assert target_pair_q == output

    input = examples + queries
    target = (
        "SELECT uri, array_agg(match) matches FROM (("
        + target_pair_ex
        + ") UNION ALL ("
        + target_pair_q
        + ")) U GROUP BY uri"
    )
    output = _prepare_stmt(input)
    assert target == output
