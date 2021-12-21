from lxml.etree import fromstring, tostring
from wrapping.objects.xpath.node import AXISNAMES, XPathNode, get_position
from wrapping.objects.xpath.predicate import (AttributePredicate, Conjunction,
                                              Disjunction, Predicate)


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
