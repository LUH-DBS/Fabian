from collections import UserList
from typing import Dict, List, Tuple

import regex
from lxml.etree import _Element
from wpdxf.wrapping.objects.xpath.node import XPathNode


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
            return "/", {}

        xpath_str = ""
        variables = {}
        for nstr, nvars in map(lambda x: x.xpath(), self):
            variables.update(nvars)
            xpath_str += nstr + "/"

        xpath_str = xpath_str[:-1]
        if not xpath_str.startswith("."):
            xpath_str = "/" + xpath_str
        xpath_str = regex.sub(r"\/{3,}", "//", xpath_str)
        if xpath_str.endswith("/"):
            xpath_str += "descendant-or-self::node()"
        return xpath_str, variables

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
