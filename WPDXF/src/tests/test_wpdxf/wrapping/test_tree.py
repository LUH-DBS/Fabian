from wpdxf.wrapping.objects.uritree import URITree


def test_create_trees():
    # add_path
    tree = URITree()
    ex_matches = {0}
    q_matches = {1}
    uri = "https://www.exA.com/stepA/stepC"
    tree.add_uri(uri, ex_matches=ex_matches, q_matches=q_matches)

    root = tree.root_nodes["www.exA.com"]

    assert root.ex_matches == ex_matches
    assert root.q_matches == q_matches
    assert len(root.children) == 1

    leaf = root.children["stepA"].children["stepC"]
    assert leaf.ex_matches == ex_matches
    assert leaf.q_matches == q_matches
    assert len(leaf.children) == 0
    assert leaf.uri == uri

    # create_uri_trees
    tree = URITree()
    tree.add_uri("http://www.exA.com/stepA/stepC", {1}, {0})
    tree.add_uri("http://www.exA.com/stepA/stepD", {1}, {0})
    tree.add_uri("http://www.exA.com/stepB", {0}, {0})
    tree.add_uri("http://www.exB.com/stepA", {0}, {1})

    target_keys = ["www.exA.com", "www.exB.com"]
    output = tree.root_nodes
    assert sorted(output) == target_keys

    assert len(output["www.exA.com"].leaves()) == 3
    assert len(output["www.exA.com"].children) == 2
    assert len(output["www.exB.com"].leaves()) == 1


def test_group_uris():
    tau = 2

    uritree = URITree()
    uritree.add_uri("http://www.example.com/A/A1/C", {0, 1}, {0, 4})
    uritree.add_uri("http://www.example.com/A/A1/D", {2, 3}, {1, 2})
    uritree.add_uri("http://www.example.com/B/B1/F", {0, 1}, {0, 1})
    uritree.add_uri("http://www.example.com/B/B1/G", {2, 3}, {2, 3})
    uritree.add_uri("http://www.example.com/B/B1/O", {0, 1}, {2, 3})
    uritree.add_uri("http://www.example.com/B/B2/H", set(), {5,})
    uritree.add_uri("http://www.example.com/C/C1/C", set(), {5,})
    uritree.add_uri("http://www.example.com/D/D1/D", {0, 1}, set())

    tree = uritree.root_nodes["www.example.com"]
    groups = tree.decompose(tau)
    target = {"A1", "B", "D"}
    assert target == {g.label for g in groups}

    candidates = {
        "http://www.exA.com/stepA/stepC": ({0}, {1}),
        "http://www.exA.com/stepA/stepD": ({1}, {0}),
        "http://www.exA.com/stepB": ({0, 1}, {0}),
        "http://www.exB.com/stepA": ({0, 1}, {1}),
    }

    uritree = URITree()
    uritree.add_uri("http://www.exA.com/stepA/stepC", {0}, {1})
    uritree.add_uri("http://www.exA.com/stepA/stepD", {1}, {0})
    uritree.add_uri("http://www.exA.com/stepB", {0, 1}, {0})
    uritree.add_uri("http://www.exB.com/stepA", {0, 1}, {0})

    target = [
        (
            "www.exA.com/stepA",
            ["http://www.exA.com/stepA/stepC", "http://www.exA.com/stepA/stepD"],
        ),
        ("www.exA.com/stepB", ["http://www.exA.com/stepB"],),
        ("www.exB.com/stepA", ["http://www.exB.com/stepA"],),
    ]

    output = dict(
        [
            (d.path(), [l.uri for l in d.leaves()])
            for node in uritree.root_nodes.values()
            for d in node.decompose(tau)
        ]
    )
    for t_name, t_uris in target:
        assert t_name in output
        assert sorted(output[t_name]) == sorted(t_uris)

    # stepE should be included as it follows the same path, although it does not provide an example match.
    # www.exA.com is the WebResource as stepA misses 2 and stepB misses 3.
    candidates = {
        "http://www.exA.com/stepA/stepC": ({0, 1}, {1}),
        "http://www.exA.com/stepA/stepD": ({1, 3}, {0}),
        "http://www.exA.com/stepA/stepE": ({}, {2}),
        "http://www.exB.com/stepB": ({0, 1, 2}, {0}),
    }
    uritree = URITree()
    uritree.add_uri("http://www.exA.com/stepA/stepC", {0, 1}, {1})
    uritree.add_uri("http://www.exA.com/stepA/stepD", {1, 3}, {0})
    uritree.add_uri("http://www.exA.com/stepA/stepE", {}, {2})
    uritree.add_uri("http://www.exB.com/stepB", {0, 1, 2}, {0})

    target = [
        (
            "www.exA.com/stepA",
            [
                "http://www.exA.com/stepA/stepC",
                "http://www.exA.com/stepA/stepD",
                "http://www.exA.com/stepA/stepE",
            ],
        ),
        ("www.exB.com/stepB", ["http://www.exB.com/stepB"]),
    ]

    output = dict(
        [
            (d.path(), [l.uri for l in d.leaves()])
            for node in uritree.root_nodes.values()
            for d in node.decompose(tau)
        ]
    )
    for t_name, t_uris in target:
        assert t_name in output
        assert sorted(output[t_name]) == sorted(t_uris)
