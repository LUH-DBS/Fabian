from corpus.retrieval.warc.warcrecord import get_html
from wrapping.objects.xpath.path import RelativeXPath


class WebPage:
    def __init__(self, uri) -> None:
        self.uri = uri
        self._html = None
        self.matches = {}
        # self.matches: Dict[int, Dict[ElementBase, Dict[str, List[ElementBase]]]]
        # self.matches: key -> {input elements: List[output elements]}}
        self.q_matches = {}
        # self.q_matches: key -> [input elements]

    @property
    def html(self):
        if self._html is None:
            self._html = get_html(self.uri)
        return self._html

    @property
    def all_matches(self):
        result = {}
        result.update({key: list(values) for key, values in self.matches.items()})
        result.update(self.q_matches)
        return result

    def add_match(self, key, inp, out):
        if out is None:
            self.add_query_match(key, inp)
        else:
            self.add_example_match(key, inp, out)

    def add_example_match(self, key, inp, out):
        if not key in self.matches:
            self.matches[key] = {inp: set([out])}
        elif not inp in self.matches[key]:
            self.matches[key][inp] = set([out])
        else:
            self.matches[key][inp].add(out)

    def add_query_match(self, key, inp):
        if not key in self.q_matches:
            self.q_matches[key] = set([inp])
        else:
            self.q_matches[key].add(inp)

    def input_matches(self, key=None):
        def _collect(key):
            return list(self.matches[key].keys())

        if key is None:
            return {k: _collect(k) for k in self.matches}
        if key in self.matches:
            return _collect(key)
        return []

    def output_matches(self, key=None):
        def _collect(key):
            return [v for vals in self.matches[key].values() for v in vals]

        if key is None:
            return {k: _collect(k) for k in self.matches}
        if key in self.matches:
            return _collect(key)
        return []

    def remove_matches(self, key):
        if key in self.matches:
            return self.matches.pop(key)
        return None

    def add_matches(self, example, key, value):
        if example in self.matches:
            if key in self.matches[example]:
                self.matches[example][key] += [value]
            else:
                self.matches[example][key] = [value]
        else:
            self.matches[example] = {key: [value]}

    def relative_xpaths(self, key=None):
        def _collect(key):
            return [
                RelativeXPath.new_instance(inp_element, out_element)
                for inp_element, out_elements in self.matches[key].items()
                for out_element in out_elements
            ]

        if key is None:
            return {k: _collect(k) for k in self.matches}
        if key in self.matches:
            return _collect(key)
        return []
