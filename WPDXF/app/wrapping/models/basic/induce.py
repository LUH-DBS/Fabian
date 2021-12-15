from typing import List, Tuple, Union

from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource


class BasicInduction:
    def induce(self, resource: Resource, examples: List[Example]):
        rel_paths = [p for paths in resource.out_matches.values() for p, _ in paths]
        rel_paths = sorted(set(p.rel_path for p in rel_paths))
        result = "|".join(rel_paths)
        if result:
            resource.out_xpath = result
            return result
        return resource.out_xpath


class BasicInduction2:
    def induce(self, resource: Resource, examples: List[Tuple[str, Union[str, None]]]):
        rel_paths = [p for paths in resource.out_matches.values() for p, _ in paths]
        rel_paths = sorted(set(p.rel_path for p in rel_paths))
        print(rel_paths)
