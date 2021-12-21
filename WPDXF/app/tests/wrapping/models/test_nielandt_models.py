from wrapping.models.basic.evaluate import BasicEvaluator
from wrapping.models.nielandt.align import align
from wrapping.models.nielandt.reduce import NielandtReducer
from wrapping.models.nielandt.utils import backtrack, edit_distance
from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource
from wrapping.objects.webpage import WebPage
from wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wrapping.objects.xpath.path import XPath
from wrapping.objects.xpath.predicate import Conjunction, Predicate


def test_reduce():
    e = BasicEvaluator()
    examples = [Example(0, "Input1", "Output1"), Example(1, "Input2", "Output2")]

    reducer = NielandtReducer()

    # Reduce ambiguity on a single WebPage
    r = Resource("example.com", [])
    wp0 = WebPage("www.example.com")
    wp0._html = "<body><a><a><h1>Input1</h1></a><h2>Output1</h2></a><b><h2>Output1</h2></b><a><a><h1>Input2</h1></a><h2>Output2</h2></a></body>"
    r.webpages = [wp0]

    e.eval_initial(r, examples=examples, queries=[], eval_type=0)
    assert len(r.output_matches(0)) == 2
    assert len(r.output_matches(1)) == 1
    target = wp0.output_matches(0)[:1]

    reducer.reduce(r)
    assert len(r.output_matches(0)) == 1
    output = wp0.output_matches(0)
    assert target == output
    assert len(r.output_matches(1)) == 1

    # Reduce ambiguity across multiple WebPages
    r = Resource("example.com", [])
    wp0 = WebPage("www.example.com")
    wp0._html = "<body><a><a><h1>Input1</h1></a><h2>Output1</h2></a></body>"
    wp1 = WebPage("www.example.com")
    wp1._html = "<body><a><a><h1>Input1</h1></a></a><b><h2>Output1</h2></b></body>"
    wp2 = WebPage("www.example.com")
    wp2._html = "<body><a><a><h1>Input2</h1></a><h2>Output2</h2></a></body>"
    r.webpages = [wp0, wp1, wp2]

    e.eval_initial(r, examples=examples, queries=[], eval_type=0)
    assert len(r.output_matches(0)) == 2
    assert len(r.output_matches(1)) == 1

    reducer.reduce(r)
    assert len(r.output_matches(0)) == 1
    assert len(wp0.output_matches(0)) == 1
    assert len(wp1.output_matches(0)) == 0
    assert len(r.output_matches(1)) == 1

    # Reduce undecideable ambiguity
    # The first ambiguity will be resolved randommly (select first match)
    # The other ambiguity should be resolved based on the new assumption and therefore lead to the later pair.
    r = Resource("example.com", [])
    wp0 = WebPage("www.example.com")
    wp0._html = "<body><a>Input1</a><b>Output1</b><c>Output1</c></body>"
    wp1 = WebPage("www.example.com")
    wp1._html = "<body><a>Input2</a><c>Output2</c><b>Output2</b></body>"
    r.webpages = [wp0, wp1]

    e.eval_initial(r, examples=examples, queries=[], eval_type=0)

    assert len(r.output_matches(0)) == 2
    target_0 = r.output_matches(0)[:1]
    assert len(r.output_matches(1)) == 2
    target_1 = r.output_matches(1)[1:]

    reducer.reduce(r)
    assert target_0 == r.output_matches(0)
    assert target_1 == r.output_matches(1)

    examples.append(Example(2, "Input3", "Output3"))

    # Reduce without ambiguity
    r = Resource("example.com", [])
    wp0 = WebPage("www.example.com")
    wp0._html = "<body><a>Input1</a><b>Output1</b></body>"
    wp1 = WebPage("www.example.com")
    wp1._html = "<body><a>Input2</a><b>Output2</b></body>"
    wp2 = WebPage("www.example.com")
    wp2._html = "<body><a>Input3</a><b><c>Output3</c></b></body>"
    r.webpages = [wp0, wp1, wp2]

    e.eval_initial(r, examples=examples, queries=[], eval_type=0)
    assert len(r.output_matches(0)) == 1
    assert len(r.output_matches(1)) == 1
    assert len(r.output_matches(2)) == 1

    reducer.reduce(r)
    assert len(r.output_matches(0)) == 1
    assert len(r.output_matches(1)) == 1
    assert len(r.output_matches(2)) == 0


def test_edit_distance():
    ...


def test_align():
    # Running example from "Wrapper Induction by XPath Alignment", Nielandt et al. (2014)
    ex0 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )
    ex1 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="a"),
        ]
    )
    ex2 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="t",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="a"),
        ]
    )
    # Check edit_distance
    target_ex0_ex1 = 10
    # ex0, div - ex1, table (replace):  3
    # ex0, table - ex1, tr  (replace):  3
    # ex0, None - ex1, a    (insert):   4
    target_ex0_ex2 = 10
    # ex0, None - ex2, tr   (insert):   4
    # ex0, td - ex2, t      (replace):  2
    # ex0, None - ex2, a    (insert):   4
    target_ex1_ex2 = 7
    # ex1, None - ex2, div  (insert):   4
    # ex1, table - ex2, table (replace):    1
    # ex1, td - ex2, t      (replace):  2
    edit_matrix = edit_distance(ex0, ex1)
    assert target_ex0_ex1 == edit_matrix[-1, -1], edit_matrix
    edit_matrix = edit_distance(ex2, ex0)
    assert target_ex0_ex2 == edit_matrix[-1, -1], edit_matrix
    edit_matrix = edit_distance(ex2, ex1)
    assert target_ex1_ex2 == edit_matrix[-1, -1], edit_matrix

    target_ex0 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode.new_self(),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode.new_self(),
        ]
    )
    target_ex1 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode.new_self(),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="a"),
        ]
    )
    target_ex2 = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="t",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="a"),
        ]
    )

    output = align([ex0, ex1, ex2])
    assert any(str(out) == str(target_ex0) for out in output)
    assert any(str(out) == str(target_ex1) for out in output)
    assert any(str(out) == str(target_ex2) for out in output)
