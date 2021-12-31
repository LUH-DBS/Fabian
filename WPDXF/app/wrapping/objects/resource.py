from collections import defaultdict

from wrapping.objects.webpage import WebPage


class Resource:
    def __init__(self, id, webpages) -> None:
        self.id = id
        self.webpages = [WebPage(wp) for wp in webpages]
        self.out_xpath = ""

    def remove_webpage(self, wp):
        self.webpages.remove(wp)

    def output_matches(self, key=None):
        if key is None:
            matches = defaultdict(list)
            for wp in self.webpages:
                for k, vals in wp.output_matches(key).items():
                    matches[k].extend(vals)
            return dict(matches)

        return [(val, wp) for wp in self.webpages for val in wp.output_matches(key)]

    def relative_xpaths(self, key=None):
        if key is None:
            matches = defaultdict(list)
            for wp in self.webpages:
                for k, vals in wp.relative_xpaths(key).items():
                    matches[k].extend((v, wp) for v in vals)
            return dict(matches)

        return [(val, wp) for wp in self.webpages for val in wp.relative_xpaths(key)]

    def matched_examples(self):
        return set.union(*[set(wp.matches) for wp in self.webpages])

    def matched_queries(self):
        return set.union(*[set(wp.q_matches) for wp in self.webpages])
