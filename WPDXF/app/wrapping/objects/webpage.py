from corpus.retrieval.warc.warcrecord import get_html


class WebPage:
    def __init__(self, uri) -> None:
        self.uri = uri
        self._html = None
        self.inp_matches = None
        self.out_matches = None
        self.q_matches = None

    @property
    def html(self):
        if self._html is None:
            self._html = get_html(self.uri)
        return self._html

    def all_out_matches(self):
        return [v for vals in self.out_matches.values() for v in vals]

    def all_inp_matches(self):
        return [v for vals in self.inp_matches.values() for v in vals]
