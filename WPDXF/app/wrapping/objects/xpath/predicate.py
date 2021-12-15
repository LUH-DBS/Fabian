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
    def __init__(self, left, comp=None, right=None, is_attribute=False) -> None:
        if right is not None:
            comp = comp or COMPARATOR.EQ
        assert not ((comp is None) ^ (right is None))

        if is_attribute:
            left = f"@{left}"
            right = self._escape_val(right)

        self.left = left
        self.comp = comp
        self.right = right

    def _escape_val(self, val: object):
        if isinstance(val, str):
            return f'"{val}"'
        else:
            return val

    def __str__(self) -> str:
        if self.left == "position()" and self.comp == COMPARATOR.EQ:
            return f"{self.right}"
        if self.comp is None:
            return f"{self.left}"
        return f"{self.left}{self.comp}{self.right}"

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Predicate):
            return False
        return (
            self.left == __o.left and self.comp == __o.comp and self.right == __o.right
        )

    def __ne__(self, __o: object) -> bool:
        return ~self.__eq__(__o)


class Conjunction(UserList):
    def __str__(self) -> str:
        return "".join([f"[{str(p)}]" for p in self])


class Disjunction(UserList):
    def __str__(self) -> str:
        return " or ".join(map(str, self))


if __name__ == "__main__":
    p1 = Predicate(left="position()", right="1")
    p2 = Predicate(left="position()", right="2")
    print(p1 == p2)
