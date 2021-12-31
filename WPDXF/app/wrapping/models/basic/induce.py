from typing import List

from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource


class BasicInduction:
    # A basic induction method used for early testing, returns a conjunction of all xpaths.
    def induce(self, resource: Resource, examples: List[Example]):
        rel_paths = [p for paths in resource.out_matches.values() for p, _ in paths]
        rel_paths = sorted(set(p.rel_path for p in rel_paths))
        result = "|".join(rel_paths)
        if result:
            resource.out_xpath = result
            return result
        return resource.out_xpath