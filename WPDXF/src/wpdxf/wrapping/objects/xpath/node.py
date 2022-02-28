from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import List

from lxml.etree import ElementBase, _Element
from wpdxf.wrapping.objects.xpath.predicate import (AttributePredicate,
                                                    Predicate)


class AXISNAMES(str, Enum):
    ANC = "ancestor"
    ANOS = "ancestor-or-self"
    ATTR = "attribute"
    CHLD = "child"
    DESC = "descendant"
    DEOS = "descendant-or-self"
    FOLW = "following"
    FSIB = "following-sibling"
    NS = "namespace"
    PAR = "parent"
    PREC = "preceding"
    PSIB = "preceding-sibling"
    SELF = "self"


def get_position(element: _Element) -> int:
    """Returns the position of an element with respect to all siblings with the same tag.
    Value returns the position() predicate of the element

    Args:
        element (_Element): Target element

    Returns:
        int: Position of 'element' (position > 1).
    """
    return int(element.xpath(f"count(preceding-sibling::{element.tag})")) + 1


@dataclass
class XPathNode:
    axisname: AXISNAMES = None
    nodetest: str = None
    predicates: List[List[Predicate]] = None
    _predicates: List[List[Predicate]] = None

    def __post_init__(self):
        self.axisname = self.axisname or AXISNAMES.CHLD
        self.nodetest = self.nodetest or "node()"
        self.predicates = self.predicates or []
        self._predicates = self._predicates or []

    def xpath(self) -> str:
        def _prepare_predicates(predicates: List[List[Predicate]]):
            predicate_str = ""
            variables = {}
            cnt = count()
            for _list in predicates:
                pstr = ""
                for _pstr, _pvars in map(lambda x: x.xpath(), _list):
                    # for key, val in _pvars.items():
                    #     c = str(next(cnt))
                    #     _pstr = _pstr.replace("$" + key, "$" + key + c)
                    #     variables[key + c] = val
                    variables.update(_pvars)
                    pstr += _pstr + " or "
                predicate_str += "[" + pstr[:-4] + "]"
            return predicate_str, variables

        predicates = self.predicates + self._predicates
        variables = {}
        if predicates:
            predicate_str, variables = _prepare_predicates(predicates)
        else:
            if self.axisname is AXISNAMES.DEOS:
                return "", variables
            if self.axisname is AXISNAMES.SELF:
                return ".", variables
            if self.axisname is AXISNAMES.PAR:
                return "..", variables
            predicate_str, variables = "", {}

        if self.nodetest == "node()":
            nodetest = "*"
        else:
            nodetest = self.nodetest

        if self.axisname is AXISNAMES.CHLD:
            return nodetest + predicate_str, variables
        return f"{self.axisname}::{nodetest}" + predicate_str, variables

    def add_predicate(self, left, right=None, comp=None, variables=None):
        p = Predicate(left, right=right, comp=comp, variables=variables)
        self.predicates.append([p])
        return p

    def add_attribute(self, left, right=None, comp=None):
        a = AttributePredicate(left, right=right, comp=comp)
        self.predicates.append([a])
        return a

    @staticmethod
    def new_instance(element: _Element):
        """Returns a new instance based on an lxml.etree._Element.
        The resulting XPathNode matches the 'element' in terms of nodetest and predicate position().
        """
        position = Predicate("position()", right=get_position(element))
        return XPathNode(nodetest=element.tag, predicates=[[position]])

    @staticmethod
    def self_node(nodetest=None, predicates=[]):
        return XPathNode(
            axisname=AXISNAMES.SELF, nodetest=nodetest, predicates=predicates
        )


if __name__ == "__main__":
    p0 = Predicate("position()", right=1)
    p1 = AttributePredicate("term", right="Test Value")
    p2 = AttributePredicate("term", right="Test Value2")
    node = XPathNode(predicates=[[p0], [p1, p2]])

    print(p0.xpath())
    print(node.xpath())
