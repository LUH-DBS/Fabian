import logging
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

PREPARED_XPATHS = {
    "eq": "//*[token_equals(string(), $term)]",
    "cn": "//*[token_contains(text(), $term)]",
}


@namespace
def token_equals(context, _string, _other):
    s_iter = tp.tokenize_str_iter(_string, ignore_stopwords=False)
    o_iter = tp.tokenize_str_iter(_other, ignore_stopwords=False)

    while True:
        s_val = next(s_iter, None)
        o_val = next(o_iter, None)

        if s_val is None and o_val is None:
            return True
        if s_val is None or o_val is None or s_val != o_val:
            return False


@namespace
def token_contains(context, _string, _other):
    o_tokens = tp.tokenize_str(_other, ignore_stopwords=False)
    if o_tokens:
        o_tokens, _ = zip(*o_tokens)
    else:
        return True

    for text in _string:
        tokens = tp.tokenize_str(text, ignore_stopwords=False)
        if not tokens or len(tokens) > len(o_tokens):
            return False
        else:
            tokens, _ = zip(*tokens)
        if any(
            tokens[i : i + len(o_tokens)] == o_tokens
            for i in range(len(tokens) - len(o_tokens) + 1)
        ):
            return True
    return False


def xpath(
    query: str, query_vars: dict, element: etree._Element, path: str = None, **kwargs
) -> list:
    path = path or ""
    query = query.replace(ABS_PATH_VAR, path)
    try:
        _xpath = etree.XPath(
            query, namespaces={"re": "http://exslt.org/regular-expressions"}
        )
        out = _xpath(element, **query_vars, **kwargs)
        return out
    except etree.Error as e:
        logging.exception(f"XPATH Exception for: {query}, {query_vars}")
        return []


class BasicEvaluator:
    def __init__(self, input_xpath: str = None, output_xpath: str = None) -> None:
        self.input_xpath = input_xpath or PREPARED_XPATHS["cn"]
        self.output_xpath = output_xpath or PREPARED_XPATHS["eq"]

    def evaluate_initial(
        self, resource: Resource, examples: List[Example], queries: List[Query] = None,
    ):
        for wp in resource.webpages.copy():
            try:
                example_outputs = self.evaluate_wp(wp, self.output_xpath, {}, examples)
                for (pair, inp), outs in example_outputs.items():

                    [wp.add_example(pair, inp, out) for out in outs]

            except Exception as e:
                # Catch any etree.ParserError, timeout or other exceptions.
                logging.exception("Error on parsing " + wp.uri)
                print(format_exc())
                resource.remove_webpage(wp)

    def evaluate(self, resource: Resource, examples, queries):
        result = defaultdict(list)
        pairs = queries + [Query(ex.inp) for ex in examples]
        xpath, xvars = resource._xpath, resource._vars

        for wp in resource.webpages.copy():
            query_outputs = self.evaluate_wp(wp, xpath, xvars, pairs)
            for (pair, inp), outs in query_outputs.items():
                for out in outs:
                    result[pair].append((inp, out))

        return result

    def evaluate_wp(self, wp: WebPage, xpath: str, xvars: dict, queries):
        query_inputs = self._evaluate_initial(wp, queries)
        return self._evaluate_pairs(xpath, xvars, query_inputs)

    def _evaluate_initial(
        self, wp: WebPage, pairs: List[Pair]
    ) -> Dict[Pair, List[etree._Element]]:
        tree = etree.HTML(wp.html)
        return {
            pair: xpath(self.input_xpath, {}, tree, term=regex.escape(pair.inp))
            for pair in pairs
        }

    def _evaluate_pairs(
        self,
        xpath_str: str,
        xvars: dict,
        pair_inputs: Dict[Pair, List[etree._Element]],
    ) -> dict:
        result = defaultdict(list)
        for pair, elements in pair_inputs.items():
            for inp in elements:
                inp_path = inp.getroottree().getpath(inp)
                if pair.out:
                    term = regex.escape(pair.out)
                else:
                    term = None
                eval_out = xpath(xpath_str, xvars, inp, path=inp_path, term=term,)
                if eval_out:
                    result[pair, inp] = eval_out
        return dict(result)
