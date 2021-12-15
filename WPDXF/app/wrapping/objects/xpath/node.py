from lxml.etree import ElementBase
from wrapping.objects.xpath.predicate import Conjunction, Predicate


def get_position(element):
    p = element.getparent()
    if p is None:
        return 1
    equal_siblings = [ch for ch in p.getchildren() if ch.tag == element.tag]
    # position = 0 indicates, that the element is unique and position value can be omitted.
    # if len(equal_siblings) == 1:
    #     return 0
    return equal_siblings.index(element) + 1


class XPathNode:
    def __init__(self, *, axisname="child", nodetest="node()", predicates=None) -> None:
        self.axisname = axisname
        self.nodetest = nodetest
        self.predicates = predicates or Conjunction()
        self._predicates = Conjunction()

    def __repr__(self) -> str:
        predicates = self.predicates + self._predicates 
        if not predicates:
            if self.axisname == "descendant-or-self":
                return ""
            if self.axisname == "self":
                return "."
            if self.axisname == "parent":
                return ".."

        if self.nodetest == "node()":
            nodetest = "*"
        else:
            nodetest = self.nodetest

        if self.axisname == "child":
            return nodetest + str(predicates)
        return f"{self.axisname}::{nodetest}" + str(predicates)

    @staticmethod
    def new_instance(step: ElementBase):
        context = XPathNode(nodetest=step.tag)
        context.predicates.append(Predicate("position()", right=get_position(step)))
        return context
