from collections import defaultdict
from traceback import format_exc
from typing import Dict, Iterable, List, Set, Tuple

from lxml import etree
from wpdxf.wrapping.objects.pairs import Pair
from wpdxf.wrapping.objects.webpage import WebPage




class Resource:
    def __init__(self, identifier: str, webpages: Iterable[str]) -> None:
        self.identifier: str = identifier
        self.webpages: List[WebPage] = [WebPage(wp) for wp in webpages]
        self._xpath: str = None
        self._vars: Dict[str, str] = {}

    def remove_webpage(self, wp):
        self.webpages.remove(wp)

    def examples(
        self,
    ) -> Dict[Pair, List[Tuple[etree._Element, etree._Element, WebPage]]]:
        res = defaultdict(list)
        for wp in self.webpages:
            for pair, _list in wp.examples.items():
                res[pair].extend([(*elements, wp) for elements in _list])
        return dict(res)

    def queries(
        self,
    ) -> Dict[Pair, List[Tuple[etree._Element, etree._Element, WebPage]]]:
        res = defaultdict(list)
        for wp in self.webpages:
            for pair, _list in wp.queries.items():
                res[pair].extend([(*elements, wp) for elements in _list])
        return dict(res)

    def example_inputs(self) -> Dict[Pair, List[Tuple[etree._Element, WebPage]]]:
        res = defaultdict(list)
        for wp in self.webpages:
            for pair, element in wp.example_inputs().items():
                res[pair].append((element, wp))
        return dict(res)

    def example_outputs(self) -> Dict[Pair, List[Tuple[etree._Element, WebPage]]]:
        res = defaultdict(list)
        for wp in self.webpages:
            for pair, element in wp.example_inputs().items():
                res[pair].append((element, wp))
        return dict(res)

    def example_pairs(self) -> Set[Pair]:
        if self.webpages:
            return set.union(*(set(wp.examples) for wp in self.webpages))
        return set()

    def example_pairs(self) -> Set[Pair]:
        if self.webpages:
            return set.union(*(set(wp.queries) for wp in self.webpages))
        return set()

    def info(self):
        xpath = self._xpath
        outstr = f"Resource: {self.identifier}\nCurrent XPath: {xpath}\nNumWebpages: {len(self.webpages)}\n\n"

        input_elements = set()
        output_elements = set()
        query_elements = set()

        outstr += "Webpages:\n"
        for wp in self.webpages:

            outstr += wp.info()

            for values in wp.examples.values():
                for inp, out in values:
                    input_elements.add(inp)
                    output_elements.add(out)
            for values in wp.queries.values():
                for inp, _ in values:
                    query_elements.add(inp)

        outstr += "XPath Summary:\n"

        outstr += "Input XPaths:\n"
        for elem in input_elements:
            outstr += f"{elem}: {elem.getroottree().getpath(elem)}\n"
        outstr += "Query XPaths:\n"
        for elem in query_elements:
            outstr += f"{elem}: {elem.getroottree().getpath(elem)}\n"
        outstr += "Output XPaths:\n"
        for elem in output_elements:
            outstr += f"{elem}: {elem.getroottree().getpath(elem)}\n"

        return outstr
