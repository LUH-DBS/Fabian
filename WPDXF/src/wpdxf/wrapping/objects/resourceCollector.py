from typing import Counter, Dict, Iterator, List, Tuple

from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.utils.report import ReportWriter
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
from wpdxf.wrapping.tree.uritree import URITree


class ResourceCollector:
    def __init__(self, query_executor, tau=2, limit=100) -> None:
        self.query_executor: QueryExecutor = query_executor
        self.tau = tau
        self.limit = limit

    def collect(self, examples, queries):
        rw = ReportWriter()
        uritree = URITree()

        # Collect all websites that contain at least one example
        # and group them in a URITree structure
        with rw.start_timer("Collect Examples"):
            uritree = self.update_uritree(uritree, examples)

        # Remove all root's children subtrees (hosts) that do not cover at least tau examples.
        uritree.reduce(self.tau)

        # Collect all websites that contain at least one query
        # and update the URITree structure
        with rw.start_timer("Collect Queries"):
            uritree = self.update_uritree(uritree, queries, allow_new_roots=False)

        # Filter and group the final uritree,
        # groups are sorted descending on the amount of matching queries.
        groups, forest = self.group_uritree(uritree)
        rw.write_uri_groups(forest)

        return groups

    def update_uritree(
        self, uritree: URITree, pairs: List[Pair], allow_new_roots: bool = True,
    ):
        rw = ReportWriter()
        with rw.start_timer("DB Request"):
            partition_iter = self.query_executor.query_pairs(pairs)

        masks = self._create_masks(pairs, self.query_executor.token_dict)
        max_size = max(len(mask) for mask in masks.values())
        min_size = min(len(mask) for mask in masks.values())
        with rw.start_timer("Partition Iteration"):
            for uri, partition in partition_iter:
                uri_matches = set()
                for i in range(max(len(partition) - min_size + 1, 0)):
                    window = partition[i : i + max_size]
                    offset = window[0][1]
                    window = tuple((tid, pos - offset) for tid, pos in window)
                    for key, mask in masks.items():
                        if window[: len(mask)] == mask:
                            uri_matches.add(key)

                counter = Counter(map(lambda key: key[0], uri_matches))
                ex_matches, q_matches = set(), set()
                for pair, c in counter.most_common():
                    if c == 1 and isinstance(pair, Query):
                        q_matches.add(pair)
                    elif c == 2:
                        # c == 2 is only possible if pair is an Example,
                        # c > 2 is not possible
                        ex_matches.add(pair)

                if uri_matches:
                    uritree.add_uri(uri, ex_matches, q_matches, allow_new_roots)
        return uritree

    def _create_masks(self, pairs: List[Pair], token_dict: Dict[str, int]) -> Dict:
        masks = {}
        for pair in pairs:
            masks[(pair, 0)] = tuple(
                (token_dict[token], pos) for token, pos in pair.tok_inp
            )
            if isinstance(pair, Example):
                masks[(pair, 1)] = tuple(
                    (token_dict[token], pos) for token, pos in pair.tok_out
                )
        return masks

    def group_uritree(self, uritree: URITree) -> List[Tuple[str, List[str]]]:
        """Groups the given uris into "WebResources". Grouping is based on common uris and 
        the individual uris' matches (decision depends on 'resource_filter').

        Args:
            uris (Dict[str, Tuple[Set[int], Set[int]]]): A uri -> matches mapping (uris)
            resource_filter ([type]): A filter that can be applied to bfs_filter.

        Returns:
            List[Tuple[str, List[str]]]: A list of resources, each represented by a (partial) uri and all uris included in the resource.
        """

        def _resource_filter(node):
            # Returns True, when the node matches at least tau examples and all children cover less queries
            return (
                len(node.ex_matches) >= self.tau
                #and all(node.ex_matches > c.ex_matches for c in node.children.values()) # always True
                and all(node.q_matches > c.q_matches for c in node.children.values())
            )

        groups = []
        # filter_forest is used for visualization, has no other use.
        filtered_forest = []
        for tree in uritree.root_nodes.values():
            filter_result = tree.bfs_filter(_resource_filter)
            groups.extend(filter_result)
            if filter_result:
                filtered_forest.append(tree)
            if self.limit > 0 and len(groups) >= self.limit:
                break

        if self.limit > 0:
            groups = [
                (t.path(), [l.uri for l in t.leaves()])
                for t in sorted(groups, key=lambda t: -len(t.q_matches))
            ]

        return groups, filtered_forest
