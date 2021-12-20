from collections import UserList
from copy import deepcopy
from typing import List, Union

from lxml.etree import _Element
from wrapping.objects.xpath.node import XPathNode
from wrapping.objects.xpath.predicate import Predicate


def node_list(tail: _Element) -> List[_Element]:
    result = []
    element = tail
    while True:
        result.insert(0, element)
        element = element.getparent()
        if element is None:
            break
    return result


class XPath(UserList):
    def __str__(self) -> str:
        old_len = -1
        repr = "/".join(map(str, self))
        while old_len != len(repr):
            old_len = len(repr)
            repr = repr.replace("///", "//")
        return repr


class RelativeXPath:
    def __init__(
        self,
        start_path: Union[List[XPathNode], XPath],
        start_node: _Element = None,
        end_path: Union[List[XPathNode], XPath] = None,
        end_node: _Element = None,
        common_path: Union[List[XPathNode], XPath] = None,
    ) -> None:
        self.start_node = start_node
        self.end_node = end_node

        self.common_path = XPath(
            common_path
            or [
                XPathNode(axisname="descendant-or-self"),
                XPathNode(axisname="descendant-or-self"),
            ]
        )
        self.start_path = XPath(start_path)
        self.end_path = XPath(end_path or [XPathNode(axisname="self")])

    @staticmethod
    def new_instance(start: _Element, end: _Element):
        start_path = [XPathNode(axisname="self")]
        end_path = []
        root_element = end
        # If start and end are the same element, the relative XPath is trivial: "."
        # Due to the structure of ElementTrees, there is always at least one common 'root' element.
        if start != end:
            start_elements = node_list(start)
            end_elements = node_list(end)

            min_len = min(len(start_elements), len(end_elements))
            for idx in range(min_len):
                if start_elements[idx] != end_elements[idx]:
                    break
            # If one path contains the other,
            # the first difference is the next step of the longer path.
            else:
                idx += 1

            root_element = end_elements[idx - 1]
            start_path += XPath(map(XPathNode.new_instance, start_elements[idx:]))
            end_path += XPath(map(XPathNode.new_instance, end_elements[idx - 1 :]))

        relativeXPath = RelativeXPath(start_path, start, end_path, end)

        test = root_element.xpath(str(relativeXPath.start_path))
        assert len(test) == 1 and (
            test[0] == relativeXPath.start_node
        ), f"{str(relativeXPath)}\n{start_path}"
        test = root_element.xpath(str(relativeXPath.end_path[1:]))
        assert (
            len(test) == 1 and test[0] == relativeXPath.end_node
        ), f"{str(relativeXPath)}\n{end_path}"
        test = root_element.xpath(
            str(relativeXPath.common_path + relativeXPath.end_path[:1])
        )
        assert (
            root_element in test
        ), f"{str(relativeXPath.common_path + relativeXPath.end_path[:1])}\n{relativeXPath.end_node.getroottree().getpath(relativeXPath.end_node)}\n{start_path}\n{end_path}\n{test}"
        test = relativeXPath.end_node.xpath(str(relativeXPath))
        assert (
            len(test) == 1 and test[0] == relativeXPath.end_node
        ), f"{str(relativeXPath)}\n{start_path}\n{end_path}\n{relativeXPath.end_node.getroottree().getpath(relativeXPath.end_node)}"

        return relativeXPath

    def as_xpath(self, start_node=None, abs_start_path=None) -> str:
        start_node = self.start_node if start_node is None else start_node
        assert not (start_node is None and abs_start_path is None)
        abs_start_path = abs_start_path or start_node.getroottree().getpath(start_node)

        root = deepcopy(self.end_path[0])
        root._predicates.append(Predicate(str(self.start_path), right=abs_start_path))
        return str(self.common_path + [root] + self.end_path[1:])

    def __str__(self) -> str:
        return self.as_xpath()

    @property
    def root(self) -> XPathNode:
        """Returns the root node's XPathNode of the (smallest) subtree
           that contains the start element and the end element.

        Returns:
            XPathNode: Subtree root.
        """
        return self.end_path[0]

    @property
    def xpath(self) -> XPath:
        return self.common_path + self.end_path

    def abs_start_path(self):
        return self.start_node.getroottree().getpath(self.start_node)


if __name__ == "__main__":
    from lxml import etree, html

    text = """
    <html><body><div><a><val id="input">Input</val></a><div>Bla</div></div><div><val id="output">Output</val></div></body></html>
    """

    h = html.fromstring(text)
    tree = etree.ElementTree(h)
    e = tree.xpath("//val")
    print(e)
    r = RelativeXPath.new_instance(*e)
    e = tree.xpath("//*[text()='Bla']")[0]
    print(e)
    r = RelativeXPath.new_instance(e, e)

    text = "<a>Input</a><b>Output</b>"
    h = html.fromstring(text)
    tree = etree.ElementTree(h)
    e = tree.xpath("//*[child::text()]")
    print(e)
    r = RelativeXPath.new_instance(*e)

    text = "<a>Input<b>Output</b></a>"
    h = html.fromstring(text)
    tree = etree.ElementTree(h)
    e = tree.xpath("//*[child::text()]")
    print(e)
    r = RelativeXPath.new_instance(*e)
