from wrapping.tree.filter import TauMatchFilter
from wrapping.tree.uritree import URITree, group_uris


def test_create_trees():
    # add_children
    root = URITree("test", None)
    child0 = root.add_child("same")
    child1 = root.add_child("same")
    assert child0 == child1

    child2 = root.add_child("other")
    assert child0 != child2

    # add_path
    root = URITree("exA.com", None)
    ex_matches = {0}
    q_matches = {1}
    uri = "www.exA.com/stepA/stepC"
    root.add_path(
        "stepA", "stepC", ex_matches=ex_matches, q_matches=q_matches, leaf=uri,
    )

    assert root.ex_matches == ex_matches
    assert root.q_matches == q_matches
    assert len(root.children) == 1

    leaf = root.children["stepA"].children["stepC"]
    assert leaf.ex_matches == ex_matches
    assert leaf.q_matches == q_matches
    assert len(leaf.children) == 0
    assert leaf.uri == uri

    # create_uri_trees
    candidates = {
        "http://www.exA.com/stepA/stepC": ({0}, {1}),
        "http://www.exA.com/stepA/stepD": ({1}, {0}),
        "http://www.exA.com/stepB": ({0}, {0}),
        "http://www.exB.com/stepA": ({0}, {1}),
    }
    target_keys = ["www.exA.com", "www.exB.com"]
    output = URITree.create_uri_trees(candidates)
    assert sorted(output) == target_keys

    assert len(output["www.exA.com"].leaves()) == 3
    assert len(output["www.exA.com"].children) == 2
    assert len(output["www.exB.com"].leaves()) == 1


def test_group_uris():
    candidates = {
        "http://www.exA.com/stepA/stepC": ({0}, {1}),
        "http://www.exA.com/stepA/stepD": ({1}, {0}),
        "http://www.exA.com/stepB": ({0, 1}, {0}),
        "http://www.exB.com/stepA": ({0, 1}, {1}),
    }
    resource_filter = TauMatchFilter()

    target = [
        (
            "www.exA.com/stepA",
            ["http://www.exA.com/stepA/stepC", "http://www.exA.com/stepA/stepD"],
        ),
        ("www.exA.com/stepB", ["http://www.exA.com/stepB"],),
        ("www.exB.com/stepA", ["http://www.exB.com/stepA"],),
    ]

    output = group_uris(candidates, resource_filter)
    output = dict(output)
    for t_name, t_uris in target:
        assert t_name in output
        assert sorted(output[t_name]) == sorted(t_uris)

    # stepE should be included as it follows the same path, although it does not provide an example match.
    # www.exA.com is the WebResource as stepA misses 2 and stepB misses 3.
    candidates = {
        "http://www.exA.com/stepA/stepC": ({0, 1}, {1}),
        "http://www.exA.com/stepA/stepD": ({1, 3}, {0}),
        "http://www.exA.com/stepA/stepE": ({}, {2}),
        "http://www.exA.com/stepB": ({0, 1, 2}, {0}),
    }
    resource_filter = TauMatchFilter()

    target = [
        (
            "www.exA.com",
            [
                "http://www.exA.com/stepA/stepC",
                "http://www.exA.com/stepA/stepD",
                "http://www.exA.com/stepA/stepE",
                "http://www.exA.com/stepB",
            ],
        ),
    ]

    output = group_uris(candidates, resource_filter)
    output = dict(output)
    for t_name, t_uris in target:
        assert t_name in output
        assert sorted(output[t_name]) == sorted(t_uris)
