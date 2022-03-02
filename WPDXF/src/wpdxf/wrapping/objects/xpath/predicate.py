from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class COMPARATOR(str, Enum):
    EQ = "="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LEQ = "<="
    GEQ = ">="


@dataclass(frozen=True)
class Predicate:
    left: str
    right: str = None
    comp: COMPARATOR = None
    variables: Dict[str, str] = None

    def __post_init__(self):
        if self.right is not None:
            object.__setattr__(self, "comp", self.comp or COMPARATOR.EQ)
        assert not ((self.comp is None) ^ (self.right is None))

        object.__setattr__(self, "variables", self.variables or {})

    def xpath(self) -> Tuple[str, Dict[str, str]]:
        if self.left == "position()" and self.comp == COMPARATOR.EQ:
            return f"{self.right}", self.variables
        if self.comp is None:
            return f"{self.left}", self.variables
        return f"{self.left}{self.comp}{self.right}", self.variables


class AttributePredicate(Predicate):
    """Predicates regarding attributes are abbreviated with a leading '@'.
    If 'right' contains a string, it is escaped: val -> "val"
    """

    def __init__(self, left, comp=None, right=None) -> None:
        left = "@" + left
        if isinstance(right, str):
            key = "r" + str(hash(right))
            variables = {key: right}
            right = "$" + key
        else:
            variables = None
        super().__init__(left, comp=comp, right=right, variables=variables)
