from collections import defaultdict
from itertools import product
from typing import List, Tuple, Union

from lxml import etree, html
from wrapping.objects.relXPath import RelativeXPath
from wrapping.objects.resource import Resource
from wrapping.objects.webpage import WebPage


def eval_type_0(target, term):
    query = ".//*[contains(., $term)][not(descendant::*[contains(., $term)])]"
    return target.xpath(query, term=term)


def eval_type_1(target, term):
    query = ".//*[contains(translate(., $upper, $term), $term)][not(descendant::*[contains(translate(., $upper, $term), $term)])]"
    upper = term.upper()
    term = term.lower()
    return target.xpath(query, term=term, upper=upper)


def eval_type_2(target, term):
    from corpus.parsers.textparser import TextParser

    tokens = TextParser().tokenize_str(term)

    q_parts = []
    params = {}
    for i, (token, _) in enumerate(tokens):
        q_parts.append(f"contains(translate(., $upper_{i}, $term_{i}), $term_{i})")
        params[f"upper_{i}"] = token.upper()
        params[f"term_{i}"] = token
    q_parts = " and ".join(q_parts)
    query = f".//*[{q_parts}][not(descendant::*[{q_parts}])]"
    return target.xpath(query, **params)


def element_str(element):
    return etree.tostring(element, method="text", encoding="utf-8").decode("utf-8")


class BasicEvaluator:
    __EVAL_TYPES__ = (eval_type_0, eval_type_1, eval_type_2)

    def __init__(self, resource_filter) -> None:
        self.resource_filter = resource_filter

    def eval_initial(
        self,
        resource: Resource,
        examples: List[Tuple[str, Union[str, None]]],
        queries: List[Tuple[str, None]],
    ):
        for eval_func in self.__EVAL_TYPES__:
            print(f"Checking for useful resource using eval_type {eval_func}.")
            matched_examples = set()
            matched_queries = set()
            for wp in resource.webpages.copy():
                try:
                    matched_wp_ex, matched_wp_q = self._eval_wp_initial(
                        wp, examples, queries, eval_func
                    )
                    matched_examples |= matched_wp_ex
                    matched_queries |= matched_wp_q
                except etree.ParserError as e:
                    # If a webpage cannot be parsed correctly,
                    # remove it from all further considerations.
                    print(e)
                    resource.webpages.remove(wp)
                except Exception as e:
                    # There might be exceptions,
                    # which should be handled in the way as ParserErrors.
                    print(e)
                    resource.webpages.remove(wp)
            if self.resource_filter.filter(matched_examples, matched_queries):
                break
        else:
            # If none of the eval_func lead to a successfull evaluation (break),
            # return that evaluation was not successfull.
            return False
        return True

    def evaluate(self, resource: Resource, examples: List[Tuple[str, str]]):
        for wp in resource.webpages:
            out_matches = defaultdict(list)
            for key, inp_vals in wp.inp_matches.items():
                _, out = examples[key]
                for inp in inp_vals:
                    eval_out = inp.xpath(resource.out_xpath, term=out)
                    if eval_out:
                        out_matches[key].extend(
                            [RelativeXPath(inp, e_out) for e_out in eval_out]
                        )
            wp.out_matches = dict(out_matches)
        return True

    def evaluate_query(self, resource: Resource, queries: List[Tuple[str, None]]):
        result = {}
        out_xpath = resource.out_xpath
        for i in range(len(queries)):
            key_vals = []
            for wp in resource.webpages:
                for inp in wp.q_matches.get(i, []):
                    eval_out = inp.xpath(out_xpath)
                    if eval_out:
                        key_vals.extend([element_str(e) for e in eval_out])
            result[i] = key_vals
        return result

    def _eval_wp_initial(
        self,
        webpage: WebPage,
        examples: List[Tuple[str, Union[str, None]]],
        queries: List[Tuple[str, None]],
        eval_func,
    ):
        def _eval_func(pairs, target, eval_func):
            inp_matches, out_matches = {}, {}
            for i, (inp, out) in enumerate(pairs):
                eval_inp = eval_func(target, inp)
                if not eval_inp:
                    continue

                if out is not None:
                    eval_out = eval_func(target, out)
                    if not eval_out:
                        continue
                    out_matches[i] = (eval_inp, eval_out)
                inp_matches[i] = eval_inp
            return inp_matches, out_matches

        h = html.fromstring(webpage.html)
        # raises etree.ParserError on bad formatted html
        tree = etree.ElementTree(h)

        webpage.inp_matches, out_matches = _eval_func(examples, tree, eval_func)
        webpage.out_matches = {
            key: [RelativeXPath(*pair) for pair in product(*eval_pair)]
            for key, eval_pair in out_matches.items()
        }
        matched_examples = set(webpage.inp_matches)

        webpage.q_matches, _ = _eval_func(queries, tree, eval_func)
        matched_queries = set(webpage.inp_matches)

        return matched_examples, matched_queries

