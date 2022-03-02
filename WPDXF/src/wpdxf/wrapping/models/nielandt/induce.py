from typing import List

from wpdxf.wrapping.models.basic.evaluate import ABS_PATH_VAR
from wpdxf.wrapping.models.nielandt import *
from wpdxf.wrapping.objects.pairs import Example
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wpdxf.wrapping.objects.xpath.path import XPath, subtree_root


class NielandtInduction:
    def __init__(self, enrich_predicates: bool = True) -> None:
        self.enrich_predicates = enrich_predicates

    def induce(self, resource: Resource, examples: List[Example] = None):
        node_collection = [
            (subtree_root(start, end), start, end, wp)
            for _list in resource.examples().values()
            for start, end, wp in _list
        ]
        start_paths = []
        end_paths = []
        common_roots = []
        for cn, sn, en, wp in node_collection:
            start_paths.append(wp.xpath(cn, end=sn)[1:])  # ignore common node
            end_paths.append(wp.xpath(cn, end=en)[1:])
            common_roots.append([XPathNode.new_instance(cn)])
        start_path = merge(align(start_paths))
        end_path = merge(common_roots) + merge(align(end_paths))

        common_nodes, start_nodes, end_nodes, _ = zip(*node_collection)

        start_prefix = XPath([XPathNode.self_node()])
        end_prefix = XPath([XPathNode(AXISNAMES.DEOS), XPathNode(AXISNAMES.DEOS)])

        if self.enrich_predicates:
            start_prep = preprocess(
                start_path, [*zip(common_nodes, start_nodes)], prefix=start_prefix,
            )
            start_path = enrich(start_path, start_prep)

            end_prep = preprocess(
                end_path, [*zip(common_nodes, end_nodes)], prefix=end_prefix,
            )
            end_path = enrich(end_path, end_prep)

        start_path = start_prefix + start_path
        spath, svars = start_path.xpath()
        end_path[0].add_predicate(spath, right=ABS_PATH_VAR, variables=svars)
        end_path = end_prefix + end_path

        resource._xpath, resource._vars = end_path.xpath()
