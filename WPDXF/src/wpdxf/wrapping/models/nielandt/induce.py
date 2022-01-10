from typing import List

from wpdxf.wrapping.models.nielandt import *
from wpdxf.wrapping.objects.pairs import Example
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.xpath.path import RelativeXPath, VRelativeXPath, XPath


class NielandtInduction:
    def induce(self, resource: Resource, examples: List[Example] = None):
        relative_xpaths: List[RelativeXPath] = [
            val for vals in resource.relative_xpaths().values() for val, _ in vals
        ]

        start_path = merge(align([XPath(x.start_path) for x in relative_xpaths]))
        end_path = merge(align([XPath(x.end_path) for x in relative_xpaths]))

        out_xpath = VRelativeXPath(start_path=start_path, end_path=end_path)

        start_nodes = preprocess_startpath(start_path, relative_xpaths)
        end_nodes = preprocess_fullpath(out_xpath, relative_xpaths)

        start_path = enrich(start_path, start_nodes)
        end_path = enrich(end_path, end_nodes)

        resource.out_xpath = VRelativeXPath(start_path=start_path, end_path=end_path)
        return resource.out_xpath
