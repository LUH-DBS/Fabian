from os import sep
from typing import List

import numpy as np
from wpdxf.wrapping.models.nielandt.utils import edit_distance
from wpdxf.wrapping.objects.pairs import Example
from wpdxf.wrapping.objects.resource import Resource


class NielandtReducer:
    def reduce(self, resource: Resource):
        """Remove the match with the highest edit distance to all other examples over all examples.
        """
        # Select match with highest edit distance and remove it.
        out_matches = sorted(
            resource.relative_xpaths().items(), key=lambda x: -len(x[1])
        )
        max_cost = (0,)
        for i, (key, [(xpath, wp)]) in enumerate(out_matches):
            others = [v for _, vals in out_matches for v, _ in vals]
            mean_cost = np.mean(
                [
                    edit_distance(xpath.end_path, other.end_path)[-1, -1]
                    + edit_distance(xpath.start_path, other.start_path)[-1, -1]
                    for other in others
                ]
            )
            if mean_cost > max_cost[0]:
                max_cost = (mean_cost, key, wp)
        _, key, wp = max_cost
        wp.remove_examples(key)

    def reduce_ambiguity(self, resource: Resource):
        """For each example with more than one matching pair, calculate the mean edit distance between each matching pair and all pairs of the other examples. 
        As each transformation is assumed to occour exactly once in a resource, select the armin and remove the rest.

        Args:
            resource (Resource): A (already evaluated) resource.
            out_matches (list): A list of (example, matches)-Tuples.
        """
        out_matches = sorted(
            resource.relative_xpaths().items(), key=lambda x: -len(x[1])
        )
        while True:
            # Select example with highest ambiguity
            key, vals = out_matches.pop(0)
            if len(vals) == 1:
                return
            others = [v for _, vals in out_matches for v, _ in vals]
            # Select match with lowest edit distance to all other examples.
            min_cost = (np.inf,)
            for xpath, wp in vals:
                mean_cost = np.mean(
                    [
                        edit_distance(xpath.end_path, other.end_path)[-1, -1]
                        + edit_distance(xpath.start_path, other.start_path)[-1, -1]
                        for other in others
                    ]
                )
                if mean_cost < min_cost[0]:
                    min_cost = (mean_cost, xpath, wp)
            # Keep argmin, remove other matches
            for wp in resource.webpages:
                wp.remove_examples(key)
            _, xpath, wp = min_cost
            wp.add_example(key, xpath.start_node, xpath.end_node)
            # Append example to out_matches (as there is no ambiguity, it is sorted at the end).
            out_matches.append((key, [(xpath, wp)]))
