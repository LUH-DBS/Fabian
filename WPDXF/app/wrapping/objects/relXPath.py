from typing import List

from lxml.etree import Element


def get_position(element):
    p = element.getparent()
    if p is None:
        return 1
    pos = 1
    for ch in p.getchildren():
        if ch == element:
            return pos
        elif ch.tag == element.tag:
            pos += 1


class RelativeXPath:
    def __init__(self, start: Element, end: Element) -> None:
        self.start = start
        self.end = end

        start_elements = []
        while start is not None:
            start_elements = [start] + start_elements
            start = start.getparent()

        end_elements = []
        while end is not None:
            try:
                idx = start_elements.index(end)
                break
            except ValueError:
                end_elements = [end] + end_elements
                end = end.getparent()

        self._common_elements = start_elements[: idx + 1]
        self._start_elements = start_elements[idx + 1 :]
        self._end_elements = end_elements

    def __repr__(self) -> str:
        return self.rel_path

    def diff(self, other):
        max_len = min(len(self.start_elements), len(other.start_elements))
        difference = max(len(self.start_elements), len(other.start_elements)) - max_len

        for s_elem, o_elem in zip(
            self.start_elements[:max_len], other.start_elements[:max_len]
        ):
            if s_elem.tag != o_elem.tag:
                difference += 1
                break
            elif get_position(s_elem) != get_position(o_elem):
                difference += abs(get_position(s_elem) - get_position(o_elem))
                break

        max_len = min(len(self.end_elements), len(other.end_elements))
        difference += max(len(self.end_elements), len(other.end_elements)) - max_len

        for s_elem, o_elem in zip(
            self.end_elements[:max_len], other.end_elements[:max_len]
        ):
            if s_elem.tag != o_elem.tag:
                difference += 1
                break
            elif get_position(s_elem) != get_position(o_elem):
                difference += abs(get_position(s_elem) - get_position(o_elem))
                break

        return difference

    def _path_to_str(self, path):
        def element_factory(element):
            return element.tag + f"[{get_position(element)}]"

        return "/" * bool(path) + "/".join(map(element_factory, path))

    @property
    def start_elements(self) -> List[Element]:
        return self._common_elements + self._start_elements

    @property
    def start_path(self) -> str:
        return self._path_to_str(self.start_elements)

    @property
    def end_elements(self) -> List[Element]:
        return self._common_elements + self._end_elements

    @property
    def end_path(self) -> str:
        return self._path_to_str(self.end_elements)

    @property
    def rel_path(self) -> str:
        return (
            "."
            + "/.." * len(self._start_elements)
            + self._path_to_str(self._end_elements)
        )

