from collections import UserList
from copy import deepcopy
from dataclasses import dataclass
from itertools import count
from typing import Dict, List, Tuple

import regex
from lxml.etree import ElementBase, _Element
from wpdxf.wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wpdxf.wrapping.objects.xpath.predicate import Predicate


def nodelist(start: _Element = None, *, end: _Element) -> List[_Element]:
    if start is None:
        start = end.getroottree().getroot()
    result = [end]
    element = end
    while element != start:
        if element is None:
            raise ValueError("'end' is not an ancestor of 'start'")
        element = element.getparent()
        result.append(element)
    return result[::-1]


def subtree_root(e0: _Element, e1: _Element):
    if e0 == e1:
        return e0
    e0_list = nodelist(end=e0)
    e1_list = nodelist(end=e1)
    for element in e0_list[::-1]:
        if element in e1_list:
            return element


class XPath(UserList):
    """A XPath wrapper with the ability to represent the underlying list of XPathNode as a valid XPath."""

    def xpath(self) -> Tuple[str, Dict[str, str]]:
        if not self:
            return "/"
        _xpath = ""
        variables = {}
        cnt = count()
        for nstr, nvars in map(lambda x: x.xpath(), self):
            # for key, val in nvars.items():
            #     c = str(next(cnt))
            #     nstr = nstr.replace("$" + key, "$" + key + c)
            #     variables[key + c] = val
            variables.update(nvars)
            _xpath += nstr + "/"
        _xpath = _xpath[:-1]
        if not _xpath.startswith("."):
            _xpath = "/" + _xpath
        _xpath = regex.sub(r"/{3,}", "//", _xpath)
        return _xpath, variables

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

    @staticmethod
    def new_instance(start: _Element = None, *, end: _Element):
        return XPath(map(XPathNode.new_instance, nodelist(start, end=end)))


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
        root_node=None,
    ) -> None:
        super().__init__(
            start_path=start_path, end_path=end_path, common_path=common_path
        )

        self.start_node = start_node
        self.end_node = end_node
        self.root_node = root_node

    def __str__(self) -> str:
        return self.as_xpath()

    @staticmethod
    def new_instance(start_node: ElementBase, end_node: ElementBase):
        start_path = []
        end_path = [XPathNode.new_instance(end_node)]

        root_node = end_node

        if start_node != end_node:
            start_elements = nodelist(start_node)
            end_elements = nodelist(end_node)

            min_len = min(len(start_elements), len(end_elements))
            for idx in range(min_len):
                if start_elements[idx] != end_elements[idx]:
                    break
            else:
                idx += 1

            root_node = end_elements[idx - 1]

            start_elements = tuple(start_elements[idx:])
            end_elements = tuple(end_elements[idx - 1 :])

            start_path = [*map(XPathNode.new_instance, start_elements)]
            end_path = [*map(XPathNode.new_instance, end_elements)]

        relativeXPath = RelativeXPath(
            start_path=tuple(start_path),
            end_path=tuple(end_path),
            start_node=start_node,
            end_node=end_node,
            root_node=root_node,
        )

        eval_out = start_node.xpath(str(relativeXPath))
        assert eval_out == [
            end_node
        ], f"{relativeXPath}\n{end_node.getroottree().getpath(end_node)}\n{eval_out}"
        return relativeXPath

    def as_xpath(self, start_node=None, abs_start_path=None):
        start_node = self.start_node if start_node is None else start_node
        return super().as_xpath(start_node=start_node, abs_start_path=abs_start_path)
