from lxml.etree import fromstring
from wrapping.models.basic.evaluate import BasicEvaluator
from wrapping.models.nielandt.align import align
from wrapping.models.nielandt.enrichment import (_close_neighbours,
                                                 _node_names,
                                                 _preceding_sibling,
                                                 _similar_attributes,
                                                 preprocess)
from wrapping.models.nielandt.merge import merge
from wrapping.models.nielandt.reduce import NielandtReducer
from wrapping.models.nielandt.utils import edit_distance
from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource
from wrapping.objects.webpage import WebPage
from wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wrapping.objects.xpath.path import RelativeXPath, XPath
from wrapping.objects.xpath.predicate import (AttributePredicate, Conjunction,
                                              Disjunction, Predicate)


def test_reduce():
    e = BasicEvaluator()
    examples = [Example(0, "Input1", "Output1"), Example(1, "Input2", "Output2")]

    reducer = NielandtReducer()

    # Reduce ambiguity on a single WebPage
    r = Resource("example.com", [])
    wp0 = WebPage("www.example.com")
    wp0._html = "<body><a><a><h1>Input1</h1></a><h2 key='target'>Output1</h2></a><b><h2 key='error'>Output1</h2></b><a><a><h1>Input2</h1></a><h2>Output2</h2></a></body>"
    r.webpages = [wp0]

    e.eval_initial(r, examples, eval_type=0)
    assert len(r.output_matches(0)) == 2
    assert len(r.output_matches(1)) == 1
    target = list(
        filter(lambda x: x.attrib.get("key") == "target", wp0.output_matches(0))
    )

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

    e.eval_initial(r, examples, eval_type=0)
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

    e.eval_initial(r, examples, eval_type=0)

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

    e.eval_initial(r, examples, eval_type=0)
    assert len(r.output_matches(0)) == 1
    assert len(r.output_matches(1)) == 1
    assert len(r.output_matches(2)) == 1

    reducer.reduce(r)
    assert len(r.output_matches(0)) == 1
    assert len(r.output_matches(1)) == 1
    assert len(r.output_matches(2)) == 0


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

    # Alignment
    output = align([ex0, ex1, ex2])  # Output order can differ.
    assert any(out == target_ex0 for out in output)
    assert any(out == target_ex1 for out in output)
    assert any(out == target_ex2 for out in output)

    target = XPath(
        [
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="body"),
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="table"),
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(nodetest="node()",),
            XPathNode(axisname=AXISNAMES.DEOS),
        ]
    )
    output = merge(output)
    assert output == target


def test_enrichment():
    # Running example from "Predicate enrichment of aligned XPaths for wrapper induction", Nielandt et al. (2016)
    input0 = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
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
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )
    input1 = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="3")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )
    input2 = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="3")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    target0 = input0
    target1 = input1
    target2 = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode.new_self(),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="tr",
                predicates=Conjunction([Predicate("position()", right="3")]),
            ),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )
    output = align([input0, input1, input2])  # Output order can differ.
    assert any(out == target0 for out in output)
    assert any(out == target1 for out in output)
    assert any(out == target2 for out in output)

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(axisname=AXISNAMES.DEOS,),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="2")]),
            ),
            XPathNode(nodetest="div",),
            XPathNode(
                nodetest="table",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="tr",),
            XPathNode(
                nodetest="td",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    output = merge(output)
    assert output == target


def test_preprocessing():
    xpath_g = XPath(
        [
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div",),
            XPathNode(axisname=AXISNAMES.DEOS,),
            XPathNode(
                nodetest="span",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="b",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )
    assert str(xpath_g) == "/body[1]/div//span[1]/b[1]"
    html = fromstring(
        "<body><div><span><b key='target'></b></span></div><div><div><span><b key='target'></b></span></div></div><div><table><tr><td><span><b key='error'></b></span></td><td></td></tr></table></div></body>"
    )
    start_node = html
    end_nodes = html.xpath("//b[@key='target']")
    xpaths = [
        RelativeXPath.new_instance(start_node, end_node) for end_node in end_nodes
    ]
    nodes = preprocess(xpath_g, xpaths, lambda x: x.end_node)

    # Step 0:
    target_in = {
        html,
    }
    target_on = set()
    output_in, output_on = nodes[0]
    assert output_in == target_in
    assert output_on == target_on

    # Step 1:
    target_in = set(html.xpath("/body/div[1]|/body/div[2]"))
    target_on = set(html.xpath("/body/div[3]"))
    output_in, output_on = nodes[1]
    assert output_in == target_in
    assert output_on == target_on

    # Step 2:
    target_in = set(html.xpath("/body/div[1]|/body/div[2]/div"))
    target_on = set(html.xpath("/body/div[3]/table/tr/td[1]"))
    output_in, output_on = nodes[2]
    assert output_in == target_in
    assert output_on == target_on

    # Step 3:
    target_in = set(html.xpath("/body/div[1]/span|/body/div[2]/div/span"))
    target_on = set(html.xpath("/body/div[3]/table/tr/td[1]/span"))
    output_in, output_on = nodes[3]
    assert output_in == target_in
    assert output_on == target_on

    # Step 4:
    target_in = set(html.xpath("/body/div[1]/span/b|/body/div[2]/div/span/b"))
    target_on = set(html.xpath("/body/div[3]/table/tr/td[1]/span/b"))
    output_in, output_on = nodes[4]
    assert output_in == target_in
    assert output_on == target_on


def test_enrichment():
    # Preceding Sibling
    html0 = fromstring(
        "<html><head></head><body><div><div key='target'></div></div></body></html>"
    )
    html1 = fromstring(
        "<html><head></head><body><div><div key='error'></div><div key='target'></div></div></body></html>"
    )
    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
        ]
    )

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction(
                    [
                        Predicate("position()", right="1"),
                        Predicate("preceding-sibling::head"),
                    ]
                ),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
        ]
    )
    _preceding_sibling(xpath[1], html0.xpath("//body") + html1.xpath("//body"), set())
    assert xpath == target

    # Preceding sibling is the same for indicated and overflow nodes.
    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
        ]
    )

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
        ]
    )
    _preceding_sibling(xpath[1], html0.xpath("//body"), html1.xpath("//body"))
    assert xpath == target

    # Similar attributes
    html0 = fromstring(
        "<html><body><div><div><div class='name' group='1'>Frank</div></div></div></body></html>"
    )
    html1 = fromstring(
        "<html><body><div><div><div class='name'>Daisy</div></div><div><div class='name'>Jos</div></div><div><div class='name' group='2'>Lisa</div></div></div></body></html>"
    )
    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction(
                    [
                        Predicate("position()", right="1"),
                        AttributePredicate("class", right="name"),
                        AttributePredicate("group"),
                    ]
                ),
            ),
        ]
    )
    _similar_attributes(
        xpath[4],
        html0.xpath("/html/body/div/div/div")
        + html1.xpath("/html/body/div/div[3]/div"),
        set(),
    )
    assert xpath == target

    # Same as above with overflow nodes
    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    _similar_attributes(
        xpath[4],
        html0.xpath("/html/body/div/div/div")
        + html1.xpath("/html/body/div/div[3]/div"),
        html1.xpath("/html/body/div/div[position() < 3]/div"),
    )
    assert xpath == target, str(xpath)

    # Node names
    html0 = fromstring("<html><body><div><h1><span></span></h1></div></body></html>")
    html1 = fromstring(
        "<html><body><div><div><span></span></div><p><span></span></p></div></body></html>"
    )

    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(predicates=Conjunction([Predicate("position()", right="1")])),
            XPathNode(
                nodetest="span",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(predicates=Conjunction([Predicate("position()", right="1"),])),
            XPathNode(
                nodetest="span",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    _node_names(
        xpath[3],
        html0.xpath("/html/body/div/h1") + html1.xpath("/html/body/div/div"),
        set(),
    )
    assert xpath == target, str(xpath)

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                predicates=Conjunction(
                    [
                        Predicate("position()", right="1"),
                        Disjunction([Predicate("self::h1"), Predicate("self::div")]),
                    ]
                )
            ),
            XPathNode(
                nodetest="span",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    _node_names(
        xpath[3],
        html0.xpath("/html/body/div/h1") + html1.xpath("/html/body/div/div"),
        html1.xpath("/html/body/div/p"),
    )
    assert xpath == target, str(xpath)

    # Close neighbours
    html0 = fromstring(
        """
<html>
  <body>
    <div>
      <h1>Name:</h1>
      <div><div>NameA</div></div>
    </div>
    <div>
      <h1>Other:</h1>
      <div><div>OtherA</div></div>
    </div>
  </body>
</html>"""
    )
    html1 = fromstring(
        """
<html>
  <body>
    <div>
      <h1>Name:</h1>
      <div><div>NameB</div></div>
    </div>
    <div>
      <h1>Other:</h1>
      <div><div>OtherB</div></div>
    </div>
  </body>
</html>"""
    )

    xpath = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
        ]
    )

    target = XPath(
        [
            XPathNode(
                nodetest="html",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="body",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(nodetest="div"),
            XPathNode(
                nodetest="div",
                predicates=Conjunction([Predicate("position()", right="1")]),
            ),
            XPathNode(
                nodetest="div",
                predicates=Conjunction(
                    [
                        Predicate("position()", right="1"),
                        Predicate("./../preceding-sibling::h1/text()[1]='Name:'"),
                    ]
                ),
            ),
        ]
    )

    _close_neighbours(
        xpath[4],
        html0.xpath("/html/body/div[1]/div/div")
        + html1.xpath("/html/body/div[1]/div/div"),
        html0.xpath("/html/body/div[2]/div/div")
        + html1.xpath("/html/body/div[2]/div/div"),
    )
    assert xpath == target, str(xpath)
