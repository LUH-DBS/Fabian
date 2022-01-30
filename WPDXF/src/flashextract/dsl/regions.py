from dataclasses import dataclass

from lxml.etree import _Element


@dataclass(frozen=True)
class TextRegion:
    seq: str
    start: int

    @property
    def end(self):
        return self.start + len(self.seq)

    @property
    def position(self):
        return (self.start, self.end)

    def __repr__(self) -> str:
        return f"'{self.seq}' {self.position}"

    def __len__(self):
        return len(self.seq)

    def __contains__(self, other):
        return self.start <= other.start <= other.end <= self.end

    def __getitem__(self, index):
        start = 0 if index.start is None else index.start
        assert start >= 0
        return TextRegion(self.seq[index], self.start + start)

    def relative_position(self, other):
        # relative position of self in other
        assert self in other

        s_low, s_high = self.position
        offset = other.start
        return s_low - offset, s_high - offset, offset

    def find_subregion(self, seq: str):
        idx = self.seq.find(seq)
        if idx < 0:
            return
        return TextRegion(seq, self.start + idx)

    def disjunct(self, other):
        return (self.end <= other.start) or (other.end <= self.start)


@dataclass(frozen=True)
class WebRegion:
    """Web Region is very similar to TextRegion, many parts are exact copies.
    This is done to keep both objects independent.
    """

    node: _Element
    seq: str = None
    start: int = None

    @property
    def end(self):
        if self.has_sequence():
            return self.start + len(self.seq)

    @property
    def position(self):
        return (self.start, self.end)

    def has_sequence(self):
        return not (self.start is None or self.seq is None)

    def is_ancestor(self, other):
        node = other.node
        while True:
            if node == self.node:
                return True
            if node is None:
                return False
            node = node.getparent()

    def __len__(self):
        if self.has_sequence():
            return len(self.seq)

    def __contains__(self, other):
        if self.node == other.node:
            # If both nodes specify a text region inside the same node,
            # check if the other sequences is inside the own sequence
            if self.has_sequence() and other.has_sequence():
                return self.start <= other.start <= other.end <= self.end
            # If the own node specifies a text region but not the other, return False
            if self.has_sequence():
                return False
            # If the other node specifies a text region inside the same region, return True
            return True

        # Self and other are different nodes, but self specifies a text region, return False
        if self.has_sequence():
            return False

        # Check if self is an ancestor node of other
        return self.is_ancestor(other)

    def __getitem__(self, index):
        start = 0 if index.start is None else index.start
        assert start >= 0
        if self.has_sequence():
            return WebRegion(self.node, self.seq[index], self.start + start)
        else:
            return WebRegion(self.node, self.node.text[index], start)

    def relative_position(self, other):
        assert self in other
        # assert self.has_sequence()
        if not self.has_sequence():
            return None, None, None

        s_low, s_high = self.position
        offset = other.start or 0
        return s_low - offset, s_high - offset, offset

    def find_subregion(self, xpath: str = None, seq: str = None):
        _node = self.node
        if xpath:
            eval_out = self.node.xpath(xpath)
            if len(eval_out) != 1:
                return
            _node = eval_out[0]
        idx = None
        if seq:
            idx = _node.text.find(seq)
            if idx < 0:
                return
        return WebRegion(_node, seq, idx)

    def disjunct(self, other):
        # if both regions belong to the same node, check if sequences are disjunct
        if self.node == other.node:
            return (self.end <= other.start) or (other.end <= self.start)
        # if nodes differ, check if one is an ancestor of the other
        return not (self.is_ancestor(other) or other.is_ancestor(self))

    def xpath(self, _xpath: str):
        return [*map(WebRegion, self.node.xpath(_xpath))]
