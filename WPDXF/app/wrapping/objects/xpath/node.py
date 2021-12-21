from enum import Enum

from lxml.etree import ElementBase, _Element
from wrapping.objects.xpath.predicate import Conjunction, Predicate


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


class XPathNode:
    """Wrapper for a single step (node) in an XPath.
    Maintains corresponding attributes and simplifies XPath representation.
    """

    def __init__(
        self,
        *,
        axisname: AXISNAMES = None,
        nodetest: str = None,
        predicates: Conjunction = None,
    ) -> None:
        """A single step of an XPath. This is adapted from the W3C representation.
        step := axisname::nodetest[predicates]
        See: https://www.w3.org/TR/1999/REC-xpath-19991116/#section-Location-Steps

        In this case, Predicates are considered to be in conjunctive normal form (CNF).
        It is not checked whether this is true or not.
        _predicates is used to store "meta predicates" that should not be considered nor changed
        in any calculation (e.g. the relative start_path).

        Args:
            axisname (AXISNAMES, optional): The axis to be considered. Defaults to "child".
            nodetest (str, optional): Specifies the node test if necessary. Defaults to "node()".
            predicates (Conjunction, optional): Predicates in CNF. Defaults to Conjunction().
        """
        self.axisname = axisname or AXISNAMES.CHLD
        self.nodetest = nodetest or "node()"
        self.predicates = predicates or Conjunction()
        self._predicates = Conjunction()

    def __str__(self) -> str:
        predicates = self.predicates + self._predicates
        if not predicates:
            if self.axisname is AXISNAMES.DEOS:
                return ""
            if self.axisname is AXISNAMES.SELF:
                return "."
            if self.axisname is AXISNAMES.PAR:
                return ".."

        if self.nodetest == "node()":
            nodetest = "*"
        else:
            nodetest = self.nodetest

        if self.axisname is AXISNAMES.CHLD:
            return nodetest + str(predicates)
        return f"{self.axisname}::{nodetest}" + str(predicates)

    @staticmethod
    def new_instance(step: _Element):
        """Returns a new instance based on an lxml.etree._Element.
        The resulting XPathNode matches the 'step' in terms of nodetest and predicate position().
        """
        context = XPathNode(nodetest=step.tag)
        context.predicates.append(Predicate("position()", right=get_position(step)))
        return context

    @staticmethod
    def new_self(nodetest=None, predicates=None):
        # Shortcut to get a self-referencing step.
        return XPathNode(
            axisname=AXISNAMES.SELF, nodetest=nodetest, predicates=predicates
        )
