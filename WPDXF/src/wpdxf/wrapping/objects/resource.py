from collections import defaultdict

from wpdxf.wrapping.objects.webpage import WebPage


class Resource:
    def __init__(self, id, webpages) -> None:
        self.id = id
        self.webpages = [WebPage(wp) for wp in webpages]
        self.out_xpath = None

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

    def examples(self):
        if self.webpages:
            return set.union(*[set(wp.examples) for wp in self.webpages])
        return set()

    def queries(self):
        if self.webpages:
            return set.union(*[set(wp.queries) for wp in self.webpages])
        return set()

    def info(self):
        input_elements = []
        output_elements = []
        query_elements = []
        for wp in self.webpages:
            for key, inps in wp.examples.items():
                input_elements.extend(inps)
                for outs in inps.values():
                    output_elements.extend(outs)
            for key, qs in wp.queries.items():
                query_elements.extend(qs)
        print("Input")
        for elem in input_elements:
            print(elem.getroottree().getpath(elem))
        print("Output")
        for elem in output_elements:
            print(elem.getroottree().getpath(elem))
        print("Query")
        for elem in query_elements:
            print(elem.getroottree().getpath(elem))