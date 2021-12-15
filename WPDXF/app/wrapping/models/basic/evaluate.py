from collections import defaultdict
from traceback import format_exc
from typing import List

from lxml import etree, html
from lxml.etree import ElementBase
from wrapping.objects.pairs import Example, Pair, Query
from wrapping.objects.resource import Resource
from wrapping.objects.webpage import WebPage


def eval_type_0(pair: Pair):
    query = ".//*[contains(., $term)][not(descendant::*[contains(., $term)])]"
    return (query, {"term": pair.inp}) + (
        (query, {"term": pair.out}) if pair.out else (None, None)
    )


def eval_type_1(pair: Pair):
    query = ".//*[contains(translate(., $upper, $term), $term)][not(descendant::*[contains(translate(., $upper, $term), $term)])]"

    return (query, {"term": pair.inp.lower(), "upper": pair.inp.upper()}) + (
        (query, {"term": pair.out.lower(), "upper": pair.out.upper()},)
        if pair.out
        else (None, None)
    )


def eval_type_2(pair: Pair):
    def _prepare_xpath_query(tokens):
        q_parts = []
        params = {}
        for token, idx in tokens:
            q_parts.append(
                f"contains(translate(., $upper_{idx}, $term_{idx}), $term_{idx})"
            )
            params[f"upper_{idx}"] = token.upper()
            params[f"term_{idx}"] = token
        q_parts = " and ".join(q_parts)
        query = f".//*[{q_parts}][not(descendant::*[{q_parts}])]"
        return query, params

    return _prepare_xpath_query(pair.tok_inp) + (
        _prepare_xpath_query(pair.tok_out) if pair.out else (None, None)
    )


def element_str(element):
    return element.xpath("string()")
    return etree.tostring(element, method="text", encoding="utf-8").decode("utf-8")


class BasicEvaluator:
    __EVAL_TYPES__ = (eval_type_0, eval_type_1, eval_type_2)
    TOTAL_EVALS = len(__EVAL_TYPES__)

    def __init__(self, resource_filter) -> None:
        self.resource_filter = resource_filter

    def eval_initial(
        self,
        resource: Resource,
        examples: List[Example],
        queries: List[Query],
        eval_type: int,
    ):
        eval_func = self.__EVAL_TYPES__[eval_type]
        print(
            f"Checking for useful resource using eval_type {eval_func} on a total of {len(resource.webpages)} webpages"
        )
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
                print(format_exc())
                resource.webpages.remove(wp)
                continue
            except Exception as e:
                # There might be exceptions,
                # which should be handled in the way as ParserErrors.
                print(format_exc())
                resource.webpages.remove(wp)
                raise e
        if self.resource_filter.filter(matched_examples, matched_queries):
            return True

    def evaluate(self, resource: Resource, examples: List[Example]):
        for wp in resource.webpages:
            matches = {
                "true": defaultdict(lambda: defaultdict(list)),
                "false": defaultdict(lambda: defaultdict(list)),
            }
            for key, inp_vals in wp.matches["true"].items():
                for inp, out_vals in inp_vals.items():
                    old_matches = out_vals
                    q = resource.out_xpath.as_xpath(start_node=inp)
                    eval_out = inp.xpath(q)
                    eval_out = list(map(self._ensure_ElementBase, eval_out))
                    if eval_out:
                        matches["true"][key][inp].extend(
                            [val for val in eval_out if val in old_matches]
                        )
                        matches["false"][key][inp].extend(
                            [val for val in eval_out if val not in old_matches]
                        )
            wp.matches = dict(matches)
        return True

    def evaluate_query(self, resource: Resource, queries: List[Query]):
        result = {}
        for i in range(len(queries)):
            key_vals = []
            for wp in resource.webpages:
                for inp in wp.q_matches.get(i, []):
                    out_xpath = resource.out_xpath.as_xpath(start_node=inp)
                    print(wp.uri)
                    print(out_xpath)
                    eval_out = inp.xpath(out_xpath)
                    print(eval_out)
                    if eval_out:
                        key_vals.extend([element_str(e) for e in eval_out])
            result[i] = key_vals
        return result

    def _eval_wp_initial(
        self,
        webpage: WebPage,
        examples: List[Example],
        queries: List[Query],
        eval_func,
    ):
        def _eval_func(pairs, target, eval_func):
            matches = {}
            for pair in pairs:
                q_in, params_in, q_out, params_out = eval_func(pair)

                eval_inp = target.xpath(q_in, **params_in)
                eval_inp = [self._ensure_ElementBase(element) for element in eval_inp]
                if not eval_inp:
                    continue

                eval_out = []
                if isinstance(pair, Example):
                    eval_out = target.xpath(q_out, **params_out)
                    eval_out = [self._ensure_ElementBase(e) for e in eval_out]
                    if not eval_out:
                        continue

                matches[pair.id] = {key: eval_out for key in eval_inp}
            return matches

        h = html.fromstring(webpage.html)
        # raises etree.ParserError on bad formatted html
        tree = etree.ElementTree(h)

        webpage.matches["true"] = _eval_func(examples, tree, eval_func)
        matched_examples = set(webpage.matches["true"])

        query_matches = _eval_func(queries, tree, eval_func)
        webpage.q_matches = {k: list(query_matches[k]) for k in query_matches}
        matched_queries = set(webpage.q_matches)

        return matched_examples, matched_queries

    def _ensure_ElementBase(self, element):
        while not isinstance(element, ElementBase):
            element = element.getparent()
        return element
