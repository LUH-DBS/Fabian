from corpus.retrieval.warc.warcrecord import get_html
from wrapping.objects.xpath.path import RelativeXPath
from copy import deepcopy


class WebPage:
    def __init__(self, uri) -> None:
        self.uri = uri
        self._html = None
        self.matches = {"true": None, "false": None}
        # self.matches: Dict[int, Dict[ElementBase, Dict[str, List[ElementBase]]]]
        # self.matches: key -> {input elements: {"true": List[output elements], "false": List[output elements]}}
        self.q_matches = None

    @property
    def html(self):
        if self._html is None:
            self._html = get_html(self.uri)
        return self._html

    def input_matches(self, key=None, select="true"):
        def _collect(key):
            return list(self.matches[select][key].keys())

        if key is None:
            return {k: _collect(k) for k in self.matches[select]}
        if key in self.matches:
            return _collect(key)
        return []

    def output_matches(self, key=None, select="true"):
        def _collect(key):
            return [v for vals in self.matches[select][key].values() for v in vals]

        if key is None:
            return {k: _collect(k) for k in self.matches[select]}
        if key in self.matches:
            return _collect(key)
        return []

    def remove_matches(self, key, select="true"):
        if key in self.matches[select]:
            return self.matches[select].pop(key)
        return None

    def add_matches(self, example, key, value, select="true"):
        if example in self.matches[select]:
            if key in self.matches[select][example]:
                self.matches[select][example][key] += [value]
            else:
                self.matches[select][example][key] = [value]
        else:
            self.matches[select][example] = {key: [value]}

    def relative_xpaths(self, key=None, select="true"):
        def _collect(key):
            return [
                RelativeXPath.new_instance(inp_element, out_element)
                for inp_element, out_elements in self.matches[select][key].items()
                for out_element in out_elements
            ]

        if key is None:
            return {k: _collect(k) for k in self.matches[select]}
        if key in self.matches[select]:
            return _collect(key)
        return []
