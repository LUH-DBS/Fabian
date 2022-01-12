from wpdxf.corpus.retrieval.warc.warcrecord import get_html
from wpdxf.wrapping.objects.xpath.path import RelativeXPath


class WebPage:
    def __init__(self, uri) -> None:
        self.uri = uri
        self._html = None
        self.examples = {}
        # self.matches: Dict[int, Dict[ElementBase, Dict[str, List[ElementBase]]]]
        # self.matches: key -> {input element: List[output elements]}}
        self.queries = {}
        # self.q_matches: key -> [input elements]

    @property
    def html(self):
        if self._html is None:
            self._html = get_html(self.uri)
        return self._html

    def add_example(self, key, inp, out):
        if not key in self.examples:
            self.examples[key] = {inp: set([out])}
        elif not inp in self.examples[key]:
            self.examples[key][inp] = set([out])
        else:
            self.examples[key][inp].add(out)

    def add_query(self, key, inp):
        if not key in self.queries:
            self.queries[key] = set([inp])
        else:
            self.queries[key].add(inp)

    def remove_examples(self, key):
        if key in self.examples:
            return self.examples.pop(key)
        return None

    def input_elements(self, key=None):
        def _collect(key):
            return list(self.examples[key].keys())

        if key is None:
            return {k: _collect(k) for k in self.examples}
        if key in self.examples:
            return _collect(key)
        return []

    def output_elements(self, key=None):
        def _collect(key):
            return [v for vals in self.examples[key].values() for v in vals]

        if key is None:
            return {k: _collect(k) for k in self.examples}
        if key in self.examples:
            return _collect(key)
        return []

    def relative_xpaths(self, key=None):
        def _collect(key):
            return [
                RelativeXPath.new_instance(inp_element, out_element)
                for inp_element, out_elements in self.examples[key].items()
                for out_element in out_elements
            ]

        if key is None:
            return {k: _collect(k) for k in self.examples}
        if key in self.examples:
            return _collect(key)
        return []

    def info(self):
        outstr = f"Webpage: {self.uri}\n"

        outstr += "Examples:\n"
        for key, inps in self.examples.items():
            for inp, outs in inps.items():
                outstr += f"{key} - {inp}: {outs}\n"

        outstr += "Queries:\n"
        for key, inps in self.queries.items():
            for inp in inps:
                outstr += f"{key} - {inp}: \n"

        return outstr + "\n"