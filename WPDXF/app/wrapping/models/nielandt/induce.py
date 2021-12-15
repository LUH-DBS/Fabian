from typing import List

from wrapping.models.nielandt import *
from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource
from wrapping.objects.xpath.path import RelativeXPath


class NielandtInduction:
    def induce(self, resource: Resource, examples: List[Example] = None):
        relative_xpaths: List[RelativeXPath] = [
            val for vals in resource.relative_xpaths().values() for val, _ in vals
        ]

        # Induction of input (start) XPath.
        xpaths = align(list(map(lambda x: x.start_path, relative_xpaths)))
        s_xpath = merge(xpaths)
        nodes = preprocess(s_xpath, relative_xpaths, lambda x: x.start_node)
        s_xpath = enrich(s_xpath, nodes)

        # print([(i, val) for i, val in enumerate(out) if len(val[1]) > 1])

        # Induction of output (end) XPath.
        xpaths = align(list(map(lambda x: x.end_path, relative_xpaths)))
        xpath = merge(xpaths)
        nodes = preprocess(xpath, relative_xpaths, lambda x: x.end_node)
        xpath = enrich(xpath, nodes)

        # print([(i, val) for i, val in enumerate(nodes) if len(val[1]) > 1])
        resource.out_xpath = RelativeXPath(start_path=s_xpath, end_path=xpath)
        return resource.out_xpath

