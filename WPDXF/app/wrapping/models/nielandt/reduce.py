from typing import List

import numpy as np
from wrapping.models.nielandt.utils import edit_distances
from wrapping.objects.pairs import Example
from wrapping.objects.resource import Resource


class NielandtReducer:
    def reduce(self, resource: Resource, examples: List[Example] = None):
        out_matches = sorted(
            resource.relative_xpaths().items(), key=lambda x: -len(x[1])
        )
        if len(out_matches[0][1]) > 1:
            while True:
                key, vals = out_matches.pop(0)
                if len(vals) == 1:
                    break
                others = [v.xpath for _, vals in out_matches for v, _ in vals]
                min_cost = (np.inf,)
                for xpath, wp in vals:
                    mean_cost = np.mean(
                        [edit_distances(xpath.xpath, other)[-1, -1] for other in others]
                    )
                    if mean_cost < min_cost[0]:
                        min_cost = (mean_cost, xpath, wp)
                for wp in resource.webpages:
                    wp.remove_matches(key)
                _, xpath, wp = min_cost
                wp.add_matches(key, xpath.start_node, xpath.end_node)
                out_matches.append((key, [(xpath, wp)]))
        else:
            max_cost = (0,)
            for i, (key, [(xpath, wp)]) in enumerate(out_matches):
                others = [
                    v.xpath
                    for _, vals in out_matches[:i] + out_matches[i + 1 :]
                    for v, _ in vals
                ]
                mean_cost = np.mean(
                    [edit_distances(xpath.xpath, other)[-1, -1] for other in others]
                )
                if mean_cost > max_cost[0]:
                    max_cost = (mean_cost, key, wp)
            _, key, wp = max_cost
            wp.remove_matches(key)
