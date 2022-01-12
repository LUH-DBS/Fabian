from typing import Dict, List, Set, Tuple

from wpdxf.utils.report import ReportWriter
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.tree.uritree import URITree


class ResourceCollector:
    def __init__(self, query_executor, resource_filter) -> None:
        self.query_executor = query_executor
        self.resource_filter = resource_filter

    def collect(self, examples: List[Example], queries: List[Query]):
        rw = ReportWriter()
        with rw.start_timer("Query Execution"):
            uris = self.query_executor.get_uris_for(examples, queries)
        rw.write_query_result(uris)

        with rw.start_timer("Group URIs"):
            uri_groups, forest = group_uris(uris, self.resource_filter)
        rw.write_uri_groups(forest)

        return uri_groups


def group_uris(
    uris: Dict[str, Tuple[Set[int], Set[int]]], resource_filter
) -> List[Tuple[str, List[str]]]:
    """Groups the given uris into "WebResources". Grouping is based on common uris and 
    the individual uris' matches (decision depends on 'resource_filter').

    Args:
        uris (Dict[str, Tuple[Set[int], Set[int]]]): A uri -> matches mapping (uris)
        resource_filter ([type]): A filter that can be applied to bfs_filter.

    Returns:
        List[Tuple[str, List[str]]]: A list of resources, each represented by a (partial) uri and all uris included in the resource.
    """
    forest = URITree.create_uri_trees(uris)

    groups = []
    # filter_forest is used for visualization, has no other use.
    filtered_forest = []
    for tree in forest.values():
        filter_result = tree.bfs_filter(resource_filter.node_filter)
        groups.extend(filter_result)
        if filter_result:
            filtered_forest.append(tree)
    return [(t.path(), [l.uri for l in t.leaves()]) for t in groups], filtered_forest
