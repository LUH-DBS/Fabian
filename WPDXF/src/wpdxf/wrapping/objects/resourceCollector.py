import os
from collections import defaultdict
from hashlib import sha1
from typing import Counter, Dict, List, Set, Tuple

from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.utils.report import ReportWriter
from wpdxf.utils.settings import Settings
from wpdxf.utils.utils import compress_file, decompress_file
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
from wpdxf.wrapping.objects.uritree import URITree


def pair_to_cache_key(p: Pair):
    k0, k1 = (p.inp, "") if isinstance(p, Query) else p.pair
    return f"{sha1(k0.encode()).hexdigest()}_{sha1(k1.encode()).hexdigest()}"


def cache_key_to_pair(k: Tuple[str, str]):
    return Query(*k) if k[1] == "" else Example(*k)


class ResourceCollector:
    def __init__(self, query_executor, tau=2, limit=100) -> None:
        self.query_executor: QueryExecutor = query_executor
        self.tau = tau
        self.limit = limit

        self.cache_path = Settings().URL_CACHE
        _, _, self.values_in_cache = next(os.walk(self.cache_path), ([], [], []))

    def collect(self, examples, queries):
        def _collect(pairs):
            cached_pairs = [
                p for p in pairs if pair_to_cache_key(p) in self.values_in_cache
            ]
            unseen_pairs = [p for p in pairs if p not in cached_pairs]

            url_dict = defaultdict(lambda: set())
            self.collect_from_corpus(unseen_pairs, url_dict)
            self.store_to_cache(url_dict)
            self.collect_from_cache(cached_pairs, url_dict)
            return url_dict

        rw = ReportWriter()
        uritree = URITree()

        url_dict = _collect(examples)
        for uri, examples in url_dict.items():
            if examples:
                uritree.add_uri(uri, examples, {})

        uritree.reduce(self.tau)

        url_dict = _collect(queries)
        for uri, queries in url_dict.items():
            uritree.add_uri(uri, {}, queries, allow_new=False)

        rw.write_query_result(uritree.to_dict())

        groups = self.group_uritree(uritree)
        rw.write_uri_groups(groups)

        return groups

    def collect_from_cache(self, pairs: List[Pair], url_dict: defaultdict):
        for pair in pairs:
            key = pair_to_cache_key(pair)
            cachefile = os.path.join(self.cache_path, key)
            content = decompress_file(cachefile)
            for url in content.split("\n")[:-1]:
                url_dict[url].add(pair)

    def store_to_cache(self, url_dict: dict):
        for url, pairs in url_dict.items():
            for pair in pairs:
                key = pair_to_cache_key(pair)
                cachefile = os.path.join(self.cache_path, key)
                content = decompress_file(cachefile)
                compress_file(cachefile, content + url + "\n")

            self.values_in_cache.append(key)

    def collect_from_corpus(
        self, pairs: List[Pair], url_dict: defaultdict
    ) -> Dict[str, Set[Pair]]:
        if not pairs:
            return

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
                    if not window:
                        continue
                    offset = window[0][1]
                    window = tuple((tid, pos - offset) for tid, pos in window)
                    for key, mask in masks.items():
                        if window[: len(mask)] == mask:
                            uri_matches.add(key)
                counter = Counter(map(lambda key: key[0], uri_matches))
                matches = set()
                for pair, c in counter.most_common():
                    if c == 1 and isinstance(pair, Query):
                        matches.add(pair)
                    elif c == 2:
                        # c == 2 is only possible if pair is an Example,
                        # c > 2 is not possible
                        matches.add(pair)
                url_dict[uri] = matches

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

        groups = []
        for tree in uritree.root_nodes.values():
            filter_result = tree.decompose(self.tau)
            # filter_result = tree.bfs_filter(_resource_filter)
            groups.extend(filter_result)
            if self.limit > 0 and len(groups) >= self.limit:
                break

        if self.limit > 0:
            groups = [
                (t.path(), [l.uri for l in t.leaves()])
                for t in sorted(groups, key=lambda t: -len(t.q_matches))
            ]

        return groups
