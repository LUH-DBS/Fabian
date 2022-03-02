from lxml.etree import fromstring
from wpdxf.wrapping.objects.xpath.node import (AXISNAMES, XPathNode,
                                               get_position)
from wpdxf.wrapping.objects.xpath.path import XPath, nodelist, subtree_root
from wpdxf.wrapping.objects.xpath.predicate import (AttributePredicate,
                                                    Predicate)


def test_predicates():
    predicate0 = Predicate(left="position()")
    target = "position()", {}
    output = predicate0.xpath()
    assert target == output

    predicate1 = Predicate(left="position()", comp=None, right=None)
    target = "position()", {}
    output = predicate0.xpath()
    assert target == output

    assert predicate0 == predicate1

    predicate1 = Predicate(left="position()", comp=None, right=1)
    target = "1", {}
    output = predicate1.xpath()
    assert target == output

    assert predicate0 != predicate1

    predicate0 = AttributePredicate(left="key")
    target = "@key", {}
    output = predicate0.xpath()
    assert target == output

    predicate0 = AttributePredicate(left="key", right="value")
    key = f"r{hash('value')}"
    target = "@key=$" + key, {key: "value"}
    output = predicate0.xpath()
    assert target == output

    node = XPathNode()
    node.add_predicate(left="p0")
    node.add_predicate(left="p1")
    target = "*[p0][p1]", {}
    output = node.xpath()
    assert target == output

    node = XPathNode()
    node.predicates.append([Predicate(left="p0"), Predicate(left="p1")])
    target = "*[p0 or p1]", {}
    output = node.xpath()
    assert target == output

    node = XPathNode()
    node.add_attribute("p1", right="test0")
    node.predicates.append([Predicate("p0"), AttributePredicate("p1", right="test1")])
    key0 = f"r{hash('test0')}"
    key1 = f"r{hash('test1')}"
    target_vars = {key0: "test0", key1: "test1"}
    target = f"*[@p1=${key0}][p0 or @p1=${key1}]", target_vars
    output = node.xpath()
    assert target == output


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
    assert isinstance(node.predicates, list)
    target = "*", {}
    output = node.xpath()
    assert target == output

    node.nodetest = "div"
    target = "div", {}
    output = node.xpath()
    assert target == output

    node.axisname = AXISNAMES.DESC
    target = "descendant::div", {}
    output = node.xpath()
    assert target == output

    node.add_predicate(left="key")
    target = "descendant::div[key]", {}
    output = node.xpath()
    assert target == output

    n0 = XPathNode()
    n1 = XPathNode()
    assert n0 == n1

    n0.axisname = AXISNAMES.SELF
    assert n0 != n1

    html = fromstring("<div><a>First a</a><b>First b</b><a>Second a</a></div>")

    target = html
    # input
    step = XPathNode.new_instance(html)
    xpath, xvars = step.xpath()
    xpath = "/" + xpath

    output = html.xpath(xpath, **xvars)
    assert len(output) == 1
    output = output[0]
    assert target == output

    target = html.getchildren()[0]
    # input
    step = XPathNode.new_instance(target)
    _xpath, _xvars = step.xpath()
    xpath += "/" + _xpath
    xvars.update(_xvars)

    output = html.xpath(xpath, **xvars)
    assert len(output) == 1
    output = output[0]
    assert target == output

    # input
    step = XPathNode.self_node()
    _xpath, _xvars = step.xpath()
    xpath += "/" + _xpath
    xvars.update(_xvars)

    output = html.xpath(xpath, **xvars)
    assert len(output) == 1
    output = output[0]
    assert target == output


def test_nodelist():
    html = fromstring("<div><a>First a<b>First b</b></a><a>Second a</a></div>")
    input = html.getchildren()[0].getchildren()[0]
    target = [html, html.getchildren()[0], input]
    output = nodelist(end=input)
    assert output == target


def test_xpath():
    html = fromstring("<div><a>First a<b>First b</b></a><a>Second a</a></div>")
    b_element = html.getchildren()[0].getchildren()[0]
    nodes = nodelist(end=b_element)

    input = XPath()
    xpath, xvars = input.xpath()
    output = html.xpath(xpath, **xvars)
    target = []
    assert output == target

    for node in nodes:
        input.append(XPathNode.new_instance(node))
        xpath, xvars = input.xpath()
        output = html.xpath(xpath, **xvars)
        target = [node]
        assert output == target

    input = XPath()
    input.append(XPathNode(axisname=AXISNAMES.DEOS))
    target = "/descendant-or-self::node()", {}
    output = input.xpath()
    assert output == target

    target = (
        "//descendant-or-self::node()",
        {},
    )  # This is not the correct behaviour, but okay for now.
    for _ in range(3):
        input.append(XPathNode(axisname=AXISNAMES.DEOS))
        output = input.xpath()
        assert output == target

    input = XPath()
    input.append(XPathNode())
    target = "/*", {}
    output = input.xpath()
    assert output == target

    target = "//*", {}
    for _ in range(3):
        input.insert(0, XPathNode(axisname=AXISNAMES.DEOS))
        output = input.xpath()
        assert output == target


def test_relxpath():
    html = fromstring(
        "<div><a>First a<b><c>Start</c></b></a><d><e><f>End</f></e></d></div>"
    )
    start_node = html.xpath("//c")[0]
    abs_start_path = start_node.getroottree().getpath(start_node)
    end_node = html.xpath("//f")[0]

    root_element = subtree_root(start_node, end_node)

    start_path = XPath.new_instance(root_element, end=start_node)
    spath, svars = start_path.xpath()
    target = [start_node]
    output = root_element.xpath(spath, **svars)
    assert target == output, input

    end_path = XPath.new_instance(root_element, end=end_node)
    epath = [XPathNode.self_node()] + end_path[1:]
    xpath, xvars = epath.xpath()
    target = [end_node]
    output = root_element.xpath(xpath, **xvars)
    assert target == output, input

    end_path[0].add_predicate(spath, right="$TEST", variables=svars)
    xpath, xvars = end_path.xpath()
    xpath = xpath.replace("$TEST", abs_start_path)
    target = [end_node]
    output = start_node.xpath(xpath, **xvars)
    assert target == output, xpath
