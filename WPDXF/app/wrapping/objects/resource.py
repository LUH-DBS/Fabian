from collections import defaultdict

from wrapping.objects.webpage import WebPage


class Resource:
    def __init__(self, id, webpages) -> None:
        self.id = id
        self.webpages = [WebPage(wp) for wp in webpages]
        self.inp_xpath = (
            ".//*[contains(., $term)][not(descendant::*[contains(., $term)])]"
        )
        self.out_xpath = (
            ".//*[contains(., $term)][not(descendant::*[contains(., $term)])]"
        )

    def remove_webpage(self, wp):
        self.webpages.remove(wp)

    @property
    def out_matches(self) -> dict:
        matches = defaultdict(list)
        for wp in self.webpages:
            for key, vals in wp.out_matches.items():
                matches[key].extend([(v, wp) for v in vals])
        return dict(matches)

    @property
    def inp_matches(self) -> dict:
        matches = defaultdict(list)
        for wp in self.webpages:
            for key, vals in wp.inp_matches.items():
                matches[key].extend([(v, wp) for v in vals])
