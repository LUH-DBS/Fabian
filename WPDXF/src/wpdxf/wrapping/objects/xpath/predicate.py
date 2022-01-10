from collections import UserList
from enum import Enum


class COMPARATOR(str, Enum):
    EQ = "="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LEQ = "<="
    GEQ = ">="

    def __str__(self) -> str:
        return


class Predicate:
    """A XPath predicate based on W3C.
        Predicate := left comp right | left None None
        left:= Expression (str)
        comp:= COMPARATOR
        right:= Expression (str) | Value
    This class creates a wrapper and does not check correct syntax as defined by W3C. 
    It is used for simple expressions and for checking equivalence.
    See also: https://www.w3.org/TR/1999/REC-xpath-19991116/#predicates
    """

    def __init__(self, left: str, comp: COMPARATOR = None, right: str = None) -> None:
        """For any Predicate, 'left' is mandatory. 
        'right' and 'comp' can be both None or both values.
        If 'right' is not None, but 'comp' is None, 'comp' defaults to COMPARATOR.EQ.

        Args:
            left (str): Left side of predicate expression
            comp (COMPARATOR, optional): Comparator. Defaults to None.
            right (str, optional): Right side of expression. Defaults to None.
        """
        if right is not None:
            comp = comp or COMPARATOR.EQ
        assert not ((comp is None) ^ (right is None))

        self.left = left
        self.comp = comp
        self.right = right

    def __str__(self) -> str:
        if self.left == "position()" and self.comp == COMPARATOR.EQ:
            return f"{self.right}"
        if self.comp is None:
            return f"{self.left}"
        return f"{self.left}{self.comp}{self.right}"

    def __eq__(self, __o: object) -> bool:
        return (
            isinstance(__o, Predicate)
            and self.left == __o.left
            and self.comp == __o.comp
            and self.right == __o.right
        )

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)


class AttributePredicate(Predicate):
    """Predicates regarding attributes are abbreviated with a leading '@'.
    If 'right' contains a string, it is escaped: val -> "val"
    """

    def __init__(self, left, comp=None, right=None) -> None:
        left = "@" + left
        right = self._escape_val(right)
        super().__init__(left, comp=comp, right=right)

    def _escape_val(self, val: object):
        if isinstance(val, str):
            return f'"{val}"'
        else:
            return val


class Conjunction(UserList):
    """A conjunction of Predicates. In terms of XPath syntax, this can be represented as 'A and B' or '[A][B]'.
    The second is used here.
    """

    def __str__(self) -> str:
        return "".join([f"[{str(p)}]" for p in self])

    def __eq__(self, __o: object) -> bool:
        if not (hasattr(__o, "__len__") and len(self) == len(__o)):
            return False
        for p in self:
            if not any(o == p for o in __o):
                return False
        return True

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)


class Disjunction(UserList):
    """A disjunction of predicates. In terms of XPath syntax, this is represented as 'A or B'.
    """

    def __str__(self) -> str:
        return " or ".join(map(str, self))

    def __eq__(self, __o: object) -> bool:
        if not (hasattr(__o, "__len__") and len(self) == len(__o)):
            return False
        for p in self:
            if not any(o == p for o in __o):
                return False
        return True

    def __ne__(self, __o: object) -> bool:
        return not self.__eq__(__o)
