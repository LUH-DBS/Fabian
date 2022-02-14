from collections import defaultdict
from typing import Dict, List, Tuple

from lxml.etree import _Element
from wpdxf.corpus.retrieval.warc.warcrecord import get_html
from wpdxf.wrapping.objects.pairs import Pair
from wpdxf.wrapping.objects.xpath.path import XPath


class WebPage:
    def __init__(self, uri) -> None:
        self.uri: str = uri
        self._examples = defaultdict(list)
        self._queries = defaultdict(list)
        self._html: str = None
        self._xpath_cache: Dict[_Element, XPath] = {}

    def __str__(self) -> str:
        return self.uri

    @property
    def html(self):
        if self._html is None:
            self._html = get_html(self.uri)
        return self._html

    @property
    def examples(self) -> Dict[Pair, List[Tuple[_Element, _Element]]]:
        return dict(self._examples)

    @property
    def queries(self) -> Dict[Pair, List[Tuple[_Element, _Element]]]:
        return dict(self._queries)

    def add_example(self, key: Pair, inp: _Element, out: _Element):
        self._examples[key].append((inp, out))

    def add_query(self, key: Pair, inp: _Element, out: _Element = None):
        self._queries[key].append((inp, out))

    def drop_examples(self, key: Pair):
        return self._examples.pop(key, None)

    def drop_all_examples(self):
        self._examples = defaultdict(list)

    def drop_all_queries(self):
        self._queries = defaultdict(list)

    def example_inputs(self) -> Dict[Pair, List[_Element]]:
        return {pair: [inp for inp, _ in vals] for pair, vals in self._examples.items()}

    def example_outputs(self) -> Dict[Pair, List[_Element]]:
        return {pair: [out for _, out in vals] for pair, vals in self._examples.items()}

    def query_inputs(self) -> Dict[Pair, List[_Element]]:
        return {pair: [inp for inp, _ in vals] for pair, vals in self._queries.items()}

    def xpath(self, start: _Element = None, *, end: _Element) -> XPath:
        res = self._xpath_cache.get((start, end), XPath.new_instance(start, end=end))
        self._xpath_cache[(start, end)] = res
        return res

    def info(self):
        outstr = f"Webpage: {self.uri}\n"

        outstr += "Examples:\n"
        for key, values in self.examples.items():
            for inp, out in values:
                outstr += f"{key} - {inp}: {out}\n"

        outstr += "Queries:\n"
        for key, values in self.queries.items():
            for inp, _ in values:
                outstr += f"{key} - {inp}: \n"

        return outstr + "\n"
