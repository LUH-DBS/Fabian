from typing import Dict

from pyparsing import (Forward, Group, Literal, Suppress, Word, alphanums,
                       alphas, delimited_list, one_of)

BR_L, BR_R = map(Suppress, "()")
COLOR_L, COLOR_R = map(Suppress, "[]")

TYPE = one_of("str float int")("_type")
COLOR = Word(alphas)

ID = Word(alphanums)
ELEMENT = Forward()
NAMED_ELEMENT = Group(ID("identifier") + Suppress(": ") + ELEMENT)

STRUCT_LIT = Literal("Struct")
STRUCT = STRUCT_LIT("_type") + BR_L + delimited_list(NAMED_ELEMENT)("children") + BR_R

FIELD = Group(COLOR_L + COLOR("field") + COLOR_R + (STRUCT | TYPE))

SEQ_LIT = Literal("Seq")
SEQ = SEQ_LIT("_type") + BR_L + FIELD("children") + BR_R

ELEMENT <<= FIELD("children") | SEQ

SCHEMA = STRUCT | SEQ


class Field:
    STRUCT = "struct"
    SEQ = "seq"

    def __init__(
        self, name, parent, is_sequential: bool = False
    ) -> None:
        self.name = name
        self.is_sequential = is_sequential
        self.parent = parent
        self.children = None

    def __str__(self) -> str:
        return f"{self.name} ({self.is_sequential}): {self.children}"

    def __repr__(self) -> str:
        return f"{self.name} ({self.is_sequential}): {self.children}"

    def add_child(self, child, identifier=None):
        if not self.children:
            if identifier:
                self.children = {identifier: child}
            else:
                self.children = child
        else:
            self.children[identifier] = child

    def ancestors(self) -> list:
        if not self.parent:
            return []
        else:
            return [self.parent] + self.parent.ancestors()

    def is_seq_ancestor_of(self, descendant) -> bool:
        # It must be ensured that self is an actual ancestor of descendant
        node = descendant
        while True:
            if node.is_sequential:
                return True
            if node == self:
                return False
            node = node.parent

    def is_materialized(self, highlighting):
        return self.name in highlighting
        # TODO


def parse_schema(string: str) -> Dict[str, Field]:

    m = SCHEMA.parse_string(string).as_dict()
    node = Field(name="ALL", parent=None)
    schema = {"ALL": node}

    def _create_schema(m, parent: Field, schema):
        # print(m, parent)
        t = m.get("_type")
        if t == "Seq":
            node = m["children"]
            name = node["field"]
            field = Field(name=name, parent=parent, is_sequential=True)
            parent.add_child(field)
            schema[name] = field
            _create_schema(node, field, schema)
        elif t == "Struct":
            for child in m["children"]:
                identifier = child["identifier"]
                is_sequential = child.get("_type") == "Seq"
                node = child["children"]
                name = node["field"]
                field = Field(name=name, parent=parent, is_sequential=is_sequential)
                parent.add_child(field, identifier)
                schema[name] = field
                _create_schema(node, field, schema)

    _create_schema(m, node, schema)

    return schema


if __name__ == "__main__":
    schema = parse_schema("Seq([T] Struct (v: Seq([V] str)))")
    print(schema)
    schema = parse_schema("Seq([T] Struct(input: [I] str, output: [O] str))")
    print(schema)

