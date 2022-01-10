from typing import List

import numpy as np
from wpdxf.wrapping.objects.pairs import Example
from wpdxf.wrapping.objects.resource import Resource


class BasicReducer:
    def reduce(self, resource: Resource, examples: List[Example] = None):
        for wp in resource.webpages:
            done = False
            while not done:
                done = True
                ambiguities = [kv for kv in wp.out_matches.items() if len(kv[1]) > 1]
                if not ambiguities:
                    # Break if all ambiguities are resolved.
                    break

                weighted_ambs = []
                for key, vals in ambiguities:
                    others = [
                        m
                        for matches in wp.out_matches.values()
                        for m in matches
                        if m not in vals
                    ]

                    w_vals = [
                        (
                            np.mean([abs(len(val.path) - len(r.path)) for r in others])
                            if others
                            else 0,
                            key,
                            val,
                        )
                        for val in vals
                    ]
                    w_vals.sort(key=lambda x: x[0], reverse=True)

                    if w_vals[0][0] > w_vals[-1][0]:
                        weighted_ambs.append(w_vals[0])
                        done = False

                if weighted_ambs:
                    _, key, val = weighted_ambs[0]
                    wp.out_matches[key].remove(val)

        while True:
            ambiguities = [kv for kv in resource.out_matches.items() if len(kv[1]) > 1]
            if not ambiguities:
                break

            weighted_ambs = []
            for key, vals in ambiguities:
                others = [
                    m
                    for matches in resource.out_matches.values()
                    for m in matches
                    if m not in vals
                ]
                w_vals = [
                    (
                        np.mean([abs(len(val.path) - len(r.path)) for r,_ in others])
                        if others
                        else 0,
                        wp,
                        key,
                        val,
                    )
                    for val, wp in vals
                ]
                w_vals.sort(key=lambda x: x[0], reverse=True)
                weighted_ambs.append(w_vals[0])

            if weighted_ambs:
                _, wp, key, val = weighted_ambs[0]
                wp.out_matches[key].remove(val)
