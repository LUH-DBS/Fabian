import numpy as np
from wpdxf.wrapping.models.nielandt.utils import edit_distance
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.xpath.path import subtree_root


class NielandtReducer:
    def reduce(self, resource: Resource):
        """Remove the match with the highest edit distance to all other examples over all examples.
        """
        # Select match with highest edit distance and remove it.
        examples = resource.examples().items()

        max_cost = (0,)
        for i, (key, ((inp, out, wp),)) in enumerate(examples):
            others = [val for j, (_, (val,)) in enumerate(examples) if j != i]

            cn = subtree_root(inp, out)
            inp_xp = wp.xpath(cn, end=inp)
            out_xp = wp.xpath(cn, end=out)

            costs = []
            for _inp, _out, _wp in others:
                _cn = subtree_root(_inp, _out)
                costs.append(
                    edit_distance(inp_xp, _wp.xpath(_cn, end=_inp))[-1, -1]
                    + edit_distance(out_xp, _wp.xpath(_cn, end=_out))[-1, -1]
                )

            mean_cost = np.mean(costs)
            if mean_cost > max_cost[0]:
                max_cost = (mean_cost, key, wp)
        _, key, wp = max_cost
        wp.drop_examples(key)

    def reduce_ambiguity(self, resource: Resource):
        """For each example with more than one matching pair, calculate the mean edit distance between each matching pair and all pairs of the other examples. 
        As each transformation is assumed to occour exactly once in a resource, select the armin and remove the rest.

        Args:
            resource (Resource): A (already evaluated) resource.
            out_matches (list): A list of (example, matches)-Tuples.
        """
        examples = sorted(resource.examples().items(), key=lambda x: -len(x[1]))

        while True:
            # Select example with highest ambiguity
            key, vals = examples.pop(0)
            if len(vals) == 1:
                return
            others = [val for _, vals in examples for val in vals]
            # Select match with lowest edit distance to all other examples.
            min_cost = (np.inf,)
            for inp, out, wp in vals:
                cn = subtree_root(inp, out)
                inp_xp = wp.xpath(cn, end=inp)
                out_xp = wp.xpath(cn, end=out)

                costs = []
                for _inp, _out, _wp in others:
                    _cn = subtree_root(_inp, _out)
                    costs.append(
                        edit_distance(inp_xp, _wp.xpath(_cn, end=_inp))[-1, -1]
                        + edit_distance(out_xp, _wp.xpath(_cn, end=_out))[-1, -1]
                    )
                mean_cost = np.mean(costs)

                if mean_cost < min_cost[0]:
                    min_cost = (mean_cost, inp, out, wp)
            # Keep argmin, remove other matches
            [wp.drop_examples(key) for wp in resource.webpages]
            _, inp, out, wp = min_cost
            wp.add_example(key, inp, out)
            # Append example to out_matches (as there is no ambiguity, it is sorted at the end).
            examples.append((key, [(inp, out, wp)]))
