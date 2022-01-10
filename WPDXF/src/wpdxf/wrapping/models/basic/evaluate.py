from traceback import format_exc
from typing import Dict, List, Tuple

import lxml
from lxml import etree
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.webpage import WebPage


def eval_type_0(pair: Pair) -> Tuple[str, dict, str, dict]:
    """Returns XPath query for exact (case-sensitive) string matching.
    It is used to retrieve nodes that contain the exact value in their string(), 
    but only if there is no smaller portion that contains the value.

    Args:
        pair (Pair): Example or Query pair. If Query, the second part of the output returns None.

    Returns:
        Tuple[str, dict, str, dict]: Query and namespace for variables for input (and output).
    """
    query = ".//*[contains(., $term)][not(descendant::*[contains(., $term)])]"
    return (query, {"term": pair.inp}) + (
        (query, {"term": pair.out}) if pair.out else (None, None)
    )


def eval_type_1(pair: Pair) -> Tuple[str, dict, str, dict]:
    """Similar to eval_type_0, but with case-insensitive matching.

    Args:
        pair (Pair): Example or Query.

    Returns:
        Tuple[str, dict, str, dict]: Query and namespace for variables for input (and output).
    """
    query = ".//*[contains(translate(., $upper, $term), $term)][not(descendant::*[contains(translate(., $upper, $term), $term)])]"

    return (query, {"term": pair.inp.lower(), "upper": pair.inp.upper()}) + (
        (query, {"term": pair.out.lower(), "upper": pair.out.upper()},)
        if pair.out
        else (None, None)
    )


def eval_type_2(pair: Pair) -> Tuple[str, dict, str, dict]:
    """Node must contain all tokens in any order (case-insensitive).

    Args:
        pair (Pair): Example or Query.

    Returns:
        Tuple[str, dict, str, dict]: Query and namespace for variables for input (and output).
    """

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


def element_str(element) -> str:
    # Returns self-or-descendants::text() as a single joined string.
    return element.xpath("string()")


class BasicEvaluator:
    __EVAL_TYPES__ = (eval_type_0, eval_type_1, eval_type_2)
    TOTAL_EVALS = len(__EVAL_TYPES__)

    def eval_initial(
        self,
        resource: Resource,
        examples: List[Example],
        queries: List[Query],
        eval_type: int,
    ):
        """Evaluates each webpage of the given 'resource' against the specified 'eval_type'. 
        Webpages that raise Exceptions are dropped from further considerations, but Exceptions are still raised (for now).

        Args:
            resource (Resource): WebResource to be evaluated
            examples (List[Example]): Given examples
            queries (List[Query]): Given queries
            eval_type (int): Evaluation type, must be an index from __EVAL_TYPES__.

        Raises:
            e: Any error that might occur while parsing and evaluation of a webpage.
        """
        eval_func = self.__EVAL_TYPES__[eval_type]
        print(
            f"Checking for useful resource using eval_type {eval_func} on a total of {len(resource.webpages)} webpages"
        )
        for wp in resource.webpages.copy():
            try:
                self._eval_wp_initial(wp, examples + queries, eval_func)
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
                # raise e

    def _eval_wp_initial(
        self, webpage: WebPage, pairs: List[Pair], eval_func,
    ):
        # raises etree.ParserError on bad formatted html
        # h = html.fromstring(webpage.html)
        # tree = etree.ElementTree(h)
        tree = etree.HTML(webpage.html)

        for pair in pairs:
            q_in, params_in, q_out, params_out = eval_func(pair)

            eval_inp = tree.xpath(q_in, **params_in)
            if not eval_inp:
                continue

            if isinstance(pair, Query):
                [webpage.add_query(pair.id, inp) for inp in eval_inp]
            else:
                eval_out = tree.xpath(q_out, **params_out)
                for inp in eval_inp:
                    for out in eval_out:
                        webpage.add_example(pair.id, inp, out)

    def evaluate_query(
        self, resource: Resource, examples: List[Example], queries: List[Query]
    ) -> Dict[int, List[str]]:
        """Evaluates all webpages matched queries against the out_xpath provided by the resource.
        Outputs are transformed into their textual information (str).

        Args:
            resource (Resource): Resource to be evaluated
            queries (List[Query]): Given queries.

        Returns:
            Dict[int, List[str]]: Mapping from query_id to all retrieved outputs.
        """

        def _eval(pairs: List[Pair], elements):
            result = {}
            for pair in pairs:
                key_vals = []
                for wp in resource.webpages:
                    for inp in elements(wp, pair.id):
                        out_xpath = resource.out_xpath.as_xpath(start_node=inp)
                        try:
                            eval_out = inp.xpath(out_xpath)
                        except lxml.etree.XPathEvalError as e:
                            print(out_xpath)
                            print(format_exc())
                            eval_out = []
                        key_vals.extend(set(element_str(e) for e in eval_out))
                result[pair] = key_vals
            return result

        return {
            **_eval(examples, lambda wp, key: wp.examples.get(key, [])),
            **_eval(queries, lambda wp, key: wp.queries.get(key, [])),
        }
