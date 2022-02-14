from itertools import product
from traceback import format_exc
from typing import Dict, List, Tuple

import lxml
import regex
from lxml import etree
from lxml.etree import _ElementUnicodeResult
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.webpage import WebPage


class BasicEvaluator:
    def evaluate_initial(
        self, resource: Resource, examples: List[Example], queries: List[Query] = None,
    ):
        for wp in resource.webpages.copy():
            try:
                self.evaluate_wp_initial(wp, resource, examples, queries)
            except Exception as e:
                # Catch any etree.ParserError, timeout or other exceptions.
                print(format_exc())
                resource.remove_webpage(wp)

    def evaluate_wp_initial(
        self,
        wp: WebPage,
        resource: Resource,
        examples: List[Example],
        queries: List[Query] = None,
    ):
        def _evaluate_initial(
            wp: WebPage, pairs: List[Pair]
        ) -> Dict[Pair, List[etree._Element]]:
            tree = etree.HTML(wp.html)
            return {
                pair: resource.xpath(tree, term=regex.escape(pair.inp))
                for pair in pairs
            }

        example_inputs = _evaluate_initial(wp, examples)
        self.evaluate_pairs(resource, wp, example_inputs)

        query_inputs = _evaluate_initial(wp, queries)
        [wp.add_query(pair, inp) for pair, inps in query_inputs.items() for inp in inps]

    def evaluate(
        self, resource: Resource,
    ):
        for wp in resource.webpages.copy():
            self.evaluate_wp(wp, resource)

    def evaluate_wp(
        self, wp: WebPage, resource: Resource,
    ):

        query_inputs = wp.query_inputs()
        wp.drop_all_queries()
        self.evaluate_pairs(resource, wp, query_inputs)

    def evaluate_pairs(
        self,
        resource: Resource,
        wp: WebPage,
        pair_inputs: Dict[Pair, List[etree._Element]],
    ):
        for pair, elements in pair_inputs.items():
            is_example = isinstance(pair, Example)
            for inp in elements:
                inp_path = inp.getroottree().getpath(inp)
                if is_example:
                    eval_out = resource.xpath(
                        inp, path=inp_path, term=regex.escape(pair.out)
                    )
                    [wp.add_example(pair, inp, out) for out in eval_out]
                else:
                    eval_out = resource.xpath(inp, path=inp_path)
                    [wp.add_query(pair, inp, out) for out in eval_out]

