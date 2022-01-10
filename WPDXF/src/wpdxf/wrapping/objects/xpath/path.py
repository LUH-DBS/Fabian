from collections import UserList
from copy import deepcopy
from typing import List, Tuple

from lxml.etree import ElementBase, _Element
from wpdxf.wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wpdxf.wrapping.objects.xpath.predicate import Predicate


def nodelist(last: _Element) -> List[_Element]:
    result = []
    element = last
    while element is not None:
        result.append(element)
        element = element.getparent()
    return result[::-1]


class XPath(UserList):
    """A XPath wrapper with the ability to represent the underlying list of XPathNode as a valid XPath."""

    def __str__(self) -> str:
        if not self:
            return "/"
        old_len = -1
        repr = "/".join(map(str, self))
        if not repr.startswith("."):
            repr = "/" + repr
        while old_len != len(repr):
            old_len = len(repr)
            repr = repr.replace("///", "//")
        if repr.endswith("/"):
            repr += "descendant-or-self::node()"
        return repr

    def __eq__(self, __o: object) -> bool:
        return (
            hasattr(__o, "__len__")
            and len(self) == len(__o)
            and all(self[i] == __o[i] for i in range(len(self)))
        )

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)


class VRelativeXPath:
    def __init__(
        self,
        start_path: Tuple[XPathNode],
        end_path: Tuple[XPathNode],
        common_path: Tuple[XPathNode] = None,
    ) -> None:
        self.common_path = common_path or (
            XPathNode(axisname=AXISNAMES.DEOS),
            XPathNode(axisname=AXISNAMES.DEOS),
        )
        self.start_path = start_path
        self.end_path = end_path or (XPathNode.new_self(),)

    def __str__(self) -> str:
        return self.as_xpath(abs_start_path="$input")

    def full_path(self, start_node=None, abs_start_path=None):
        assert not (start_node is None and abs_start_path is None)
        abs_start_path = abs_start_path or start_node.getroottree().getpath(start_node)

        xpath_start = XPath(self.start_path)
        xpath_start.insert(0, XPathNode.new_self())
        xpath_end = deepcopy(self.end_path)
        xpath_end[0]._predicates.append(
            Predicate(str(xpath_start), right=abs_start_path)
        )
        return self.common_path, xpath_end

    def as_xpath(self, start_node=None, abs_start_path=None):
        common_path, full_path = self.full_path(start_node, abs_start_path)
        xpath = XPath(common_path) + XPath(full_path)
        return str(xpath)


class RelativeXPath(VRelativeXPath):
    def __init__(
        self,
        start_path: Tuple[XPathNode],
        end_path: Tuple[XPathNode],
        start_node,
        end_node,
        common_path: Tuple[XPathNode] = None,
    ) -> None:
        super().__init__(
            start_path=start_path, end_path=end_path, common_path=common_path
        )

        self.start_node = start_node
        self.end_node = end_node

    def __str__(self) -> str:
        return self.as_xpath()

    @staticmethod
    def new_instance(start_node: ElementBase, end_node: ElementBase):
        start_path = []
        end_path = [XPathNode.new_instance(end_node)]

        root_element = end_node

        if start_node != end_node:
            start_elements = nodelist(start_node)
            end_elements = nodelist(end_node)

            min_len = min(len(start_elements), len(end_elements))
            for idx in range(min_len):
                if start_elements[idx] != end_elements[idx]:
                    break
            else:
                idx += 1

            root_element = end_elements[idx - 1]

            start_elements = tuple(start_elements[idx:])
            end_elements = tuple(end_elements[idx - 1 :])

            start_path = [*map(XPathNode.new_instance, start_elements)]
            end_path = [*map(XPathNode.new_instance, end_elements)]

        relativeXPath = RelativeXPath(
            start_path=tuple(start_path),
            end_path=tuple(end_path),
            start_node=start_node,
            end_node=end_node,
        )

        eval_out = start_node.xpath(str(relativeXPath))
        assert eval_out == [
            end_node
        ], f"{relativeXPath}\n{end_node.getroottree().getpath(end_node)}\n{eval_out}"
        return relativeXPath

    def as_xpath(self, start_node=None, abs_start_path=None):
        start_node = self.start_node if start_node is None else start_node
        return super().as_xpath(start_node=start_node, abs_start_path=abs_start_path)
