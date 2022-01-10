import pytest
from lxml.etree import fromstring, tostring
from wrapping.objects.xpath.node import AXISNAMES, XPathNode, get_position
from wrapping.objects.xpath.path import RelativeXPath, XPath, node_list
from wrapping.objects.xpath.predicate import (
    AttributePredicate,
    Conjunction,
    Disjunction,
    Predicate,
)


def test_predicates():
    predicate0 = Predicate(left="position()")
    target = "position()"
    assert target == str(predicate0)

    predicate1 = Predicate(left="position()", comp=None, right=None)
    target = "position()"
    assert target == str(predicate1)

    assert predicate0 == predicate1

    predicate1 = Predicate(left="position()", comp=None, right=1)
    target = "1"
    assert target == str(predicate1)

    assert predicate0 != predicate1

    predicate0 = AttributePredicate(left="key")
    target = "@key"
    assert target == str(predicate0)

    predicate0 = AttributePredicate(left="key", right="value")
    target = '@key="value"'
    assert target == str(predicate0)

    conjunction = Conjunction([])
    target = ""
    assert target == str(conjunction)

    conjunction = Conjunction([Predicate(left="p0"), Predicate(left="p1")])
    target = "[p0][p1]"
    assert target == str(conjunction)

    disjunction = Disjunction([])
    target = ""
    assert target == str(disjunction)

    disjunction = Disjunction([Predicate(left="p0"), Predicate(left="p1")])
    target = "p0 or p1"
    assert target == str(disjunction)

    conjunction = Conjunction(
        [Disjunction([Predicate("p0"), Predicate("p1")]), Predicate(left="p1")]
    )
    target = "[p0 or p1][p1]"
    assert target == str(conjunction)


def test_get_position():
    html = fromstring("<div><a>First a</a><b>First b</b><a>Second a</a></div>")
    a0_element = html.find("a")
    a1_element = html.findall("a")[-1]

    target = 1
    output = get_position(html)
    assert target == output

    target = 1
    output = get_position(a0_element)
    assert target == output

    target = 2
    output = get_position(a1_element)
    assert target == output


def test_nodes():
    node = XPathNode()
    assert node.axisname is AXISNAMES.CHLD
    assert node.nodetest == "node()"
    assert isinstance(node.predicates, Conjunction)
    target = "*"
    assert target == str(node)

    node.nodetest = "div"
    target = "div"
    assert target == str(node)

    node.axisname = AXISNAMES.DESC
    target = "descendant::div"
    assert target == str(node)

    node.predicates.append(Predicate("key"))
    target = "descendant::div[key]"
    assert target == str(node)

    n0 = XPathNode()
    n1 = XPathNode()
    assert n0 == n1

    n0.axisname = AXISNAMES.SELF
    assert n0 != n1


    html = fromstring("<div><a>First a</a><b>First b</b><a>Second a</a></div>")

    target = html
    # input
    step = XPathNode.new_instance(html)
    xpath = "/" + str(step)

    output = html.xpath(xpath)
    assert len(output) == 1
    output = output[0]
    assert target == output

    target = html.getchildren()[0]
    # input
    step = XPathNode.new_instance(target)
    xpath += "/" + str(step)

    output = html.xpath(xpath)
    assert len(output) == 1
    output = output[0]
    assert target == output

    # input
    step = XPathNode.new_self()
    xpath += "/" + str(step)

    output = html.xpath(xpath)
    assert len(output) == 1
    output = output[0]
    assert target == output


def test_node_list():
    html = fromstring("<div><a>First a<b>First b</b></a><a>Second a</a></div>")
    input = html.getchildren()[0].getchildren()[0]
    target = [html, html.getchildren()[0], input]
    output = node_list(input)
    assert output == target


def test_xpath():
    html = fromstring("<div><a>First a<b>First b</b></a><a>Second a</a></div>")
    b_element = html.getchildren()[0].getchildren()[0]
    nodes = node_list(b_element)

    input = XPath()
    output = html.xpath(str(input))
    target = []
    assert output == target

    for node in nodes:
        input.append(XPathNode.new_instance(node))
        output = html.xpath(str(input))
        target = [node]
        assert output == target

    input = XPath()
    input.append(XPathNode(axisname=AXISNAMES.DEOS))
    target = "/descendant-or-self::node()"
    assert str(input) == target

    target = "//descendant-or-self::node()"  # This is not the correct behaviour, but okay for now.
    for _ in range(3):
        input.append(XPathNode(axisname=AXISNAMES.DEOS))
        assert str(input) == target

    input = XPath()
    input.append(XPathNode())
    target = "/*"
    assert str(input) == target

    target = "//*"
    for _ in range(3):
        input.insert(0, XPathNode(axisname=AXISNAMES.DEOS))
        assert str(input) == target


def test_relxpath():
    html = fromstring(
        "<div><a>First a<b><c>Start</c></b></a><d><e><f>End</f></e></d></div>"
    )
    start_node = html.xpath("//c")[0]
    end_node = html.xpath("//f")[0]

    container = []

    rel_xpath = RelativeXPath.new_instance(start_node, end_node, container)
    root_element = container[0]

    input = str(rel_xpath.start_path)
    target = [start_node]
    output = root_element.xpath(input)
    assert target == output, input

    input = str([XPathNode.new_self()] + rel_xpath.end_path[1:])
    target = [end_node]
    output = root_element.xpath(input)
    assert target == output, input

    input = str(rel_xpath)
    target = [end_node]
    output = start_node.xpath(input)
    assert target == output, input

    target = str(rel_xpath)

    rel_xpath.start_node = None
    with pytest.raises(AssertionError):
        rel_xpath.as_xpath()

    output = rel_xpath.as_xpath(start_node=start_node)
    assert output == target

    abs_start_path = start_node.getroottree().getpath(start_node)
    output = rel_xpath.as_xpath(abs_start_path=abs_start_path)
    assert output == target
