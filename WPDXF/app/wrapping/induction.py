from typing import List, Tuple

from wrapping.objects.resource import Resource


def induct(resource: Resource, examples: List[Tuple[str, str]]):
    rel_paths = [p for paths in resource.out_matches.values() for p, _ in paths]
    rel_paths = sorted(set([p.rel_path for p in rel_paths]))
    result = "|".join(rel_paths)
    resource.out_xpath = result
    return result
