from collections import defaultdict
from traceback import format_exc
from typing import Dict, List

import regex
from lxml import etree
from wpdxf.corpus.parsers.textparser import TextParser
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.webpage import WebPage

namespace = etree.FunctionNamespace(None)
tp = TextParser()

ABS_PATH_VAR = "$abs_start_path"
INITIAL_XPATH = "//*[token_equals(string(), $term)]"


@namespace
def token_equals(context, _string, _other):
    _string = tp.tokenize_str(_string, ignore_stopwords=False)
    if not _string:
        return False
    _string, _ = zip(*_string)
    _other, _ = zip(*tp.tokenize_str(_other, ignore_stopwords=False))
    return _string == _other


def xpath(
    query: str, query_vars: dict, element: etree._Element, path: str = None, **kwargs
) -> etree.XPath:
    query = query or INITIAL_XPATH
    path = path or ""
    query = query.replace(ABS_PATH_VAR, path)
    try:
        _xpath = etree.XPath(query)
        return _xpath(element, **query_vars, **kwargs)
    except etree.Error as e:
        print(query)
        print(query_vars)
        print(format_exc())
        return []


class BasicEvaluator:
    def evaluate_initial(
        self, resource: Resource, examples: List[Example], queries: List[Query] = None,
    ):
        for wp in resource.webpages.copy():
            try:
                example_inputs = self._evaluate_initial(wp, examples)
                example_outputs = self._evaluate_pairs(resource, example_inputs)
                for (pair, inp), outs in example_outputs.items():
                    [wp.add_example(pair, inp, out) for out in outs]

            except Exception as e:
                # Catch any etree.ParserError, timeout or other exceptions.
                print(format_exc())
                resource.remove_webpage(wp)

    # def evaluate_wp_initial(
    #     self,
    #     wp: WebPage,
    #     resource: Resource,
    #     examples: List[Example],
    #     queries: List[Query] = None,
    # ):
    #     example_inputs = self._evaluate_initial(wp, examples)
    #     example_outputs = self._evaluate_pairs(resource, wp, example_inputs)

    #     for (pair, inp), outs in example_outputs.items():
    #         [wp.add_example(pair, inp, out) for out in outs]

    def evaluate(self, resource: Resource, examples, queries):
        result = defaultdict(list)
        queries += [Query(ex.inp) for ex in examples]

        for wp in resource.webpages.copy():
            query_outputs = self.evaluate_wp(wp, resource, queries)
            for (pair, inp), outs in query_outputs.items():
                for out in outs:
                    result[pair].append((inp, out))
        
        return result

    def evaluate_wp(self, wp: WebPage, resource: Resource, queries):

        query_inputs = self._evaluate_initial(wp, queries)
        return self._evaluate_pairs(resource, query_inputs)

    def _evaluate_initial(
        self, wp: WebPage, pairs: List[Pair]
    ) -> Dict[Pair, List[etree._Element]]:
        tree = etree.HTML(wp.html)
        return {
            pair: xpath(INITIAL_XPATH, {}, tree, term=regex.escape(pair.inp))
            for pair in pairs
        }

    def _evaluate_pairs(
        self, resource: Resource, pair_inputs: Dict[Pair, List[etree._Element]],
    ) -> dict:
        result = defaultdict(list)
        for pair, elements in pair_inputs.items():
            for inp in elements:
                inp_path = inp.getroottree().getpath(inp)
                if pair.out:
                    term = regex.escape(pair.out)
                else:
                    term = None
                eval_out = xpath(
                    resource._xpath, resource._vars, inp, path=inp_path, term=term,
                )
                if eval_out:
                    result[pair, inp] = eval_out
        return dict(result)

        # if is_example:
        #     eval_out = xpath(
        #         resource._xpath,
        #         resource._vars,
        #         inp,
        #         path=inp_path,
        #         term=regex.escape(pair.out),
        #     )
        #     [wp.add_example(pair, inp, out) for out in eval_out]
        # else:
        #     eval_out = xpath(
        #         resource._xpath, resource._vars, inp, path=inp_path
        #     )
        #     [wp.add_query(pair, inp, out) for out in eval_out]
