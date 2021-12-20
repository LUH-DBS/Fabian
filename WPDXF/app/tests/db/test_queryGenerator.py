from wrapping.objects.pairs import Example, Query

from db.queryGenerator import _prepare_pair_stmt, _prepare_stmt, create_token_dict


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
    session.func = lambda args: ((t, i) for i, t in enumerate(sorted(args)))

    input = (session, examples + queries)
    target = (
        {
            "0": 0,  # token -> token_id
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "pos_000": 0,  # token -> pos
            "pos_001": 0,
            "pos_102": 0,
            "pos_203": 0,
            "pos_214": 1,
            "id_0": 0,  # pair_id -> pair_id
            "id_1": 1,
            "id_2": 2,
        },
        set(),
    )
    target_stmt = "SELECT token, tokenid FROM tokens WHERE token = %s OR token = %s OR token = %s OR token = %s OR token = %s"

    assert target == create_token_dict(*input)
    assert session.last_stmt == target_stmt

    # Check behavior on empty token_set
    session.func = lambda args: (("A", 0),)
    input = (session, set())
    target = ({}, set())
    assert target == create_token_dict(*input)

    # Check behavior on missing token_ids
    session.func = lambda args: (
        (t, i) for i, t in enumerate(sorted(args)) if i % 2 == 0
    )

    input = (session, examples + queries)
    target = (
        {
            "0": 0,  # token -> token_id
            "2": 2,
            "4": 4,
            "pos_000": 0,  # token -> pos
            "pos_001": 0,
            "pos_102": 0,
            "pos_203": 0,
            "pos_214": 1,
            "id_0": 0,  # pair_id -> pair_id
            "id_1": 1,
            "id_2": 2,
        },
        set(("1", "3")),
    )
    target_stmt = "SELECT token, tokenid FROM tokens WHERE token = %s OR token = %s OR token = %s OR token = %s OR token = %s"

    assert target == create_token_dict(*input)
    assert session.last_stmt == target_stmt


def test_prepare_query():
    examples = [Example(0, "This is an example input.", "This is an example output.")]
    queries = [Query(1, "This is an example query.")]

    input = examples[0]
    target_pair_ex = "SELECT uri, %(id_0)s as match FROM uris WHERE uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s \nAND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(input)s AND uriid = T0.uriid AND position = T0.position + %(pos_01input)s::integer)) AND uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s \nAND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(output)s AND uriid = T0.uriid AND position = T0.position + %(pos_01output)s::integer))"

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
    target_pair_q = "SELECT uri, %(id_1)s as match FROM uris WHERE uriid IN (SELECT T0.uriid FROM token_uri_mapping T0 WHERE T0.tokenid = %(example)s \nAND EXISTS (SELECT * FROM token_uri_mapping WHERE tokenid = %(query)s AND uriid = T0.uriid AND position = T0.position + %(pos_11query)s::integer))"

    output = _prepare_pair_stmt(input)
    assert target_pair_q == output

    input = examples + queries
    target = (
        "SELECT uri, array_agg(match) matches FROM (("
        + target_pair_ex
        + ")\nUNION ALL\n("
        + target_pair_q
        + ")) U GROUP BY uri"
    )
    output = _prepare_stmt(input)
    assert target == output
