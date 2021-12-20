from collections import defaultdict
from traceback import format_exc
from typing import Dict, List, Tuple

from lxml import etree
from lxml.etree import ElementTree
from wrapping.objects.pairs import Example, Pair, Query
from wrapping.objects.resource import Resource
from wrapping.objects.webpage import WebPage


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
                self._eval_wp_initial(wp, examples, queries, eval_func)
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

    def evaluate(self, resource: Resource, examples: List[Example]):
        # At the moment used for debugging, not relevant.
        # Evaluates all known inputs of all webpages against the given resource.out_xpath.
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

    def evaluate_query(
        self, resource: Resource, queries: List[Query]
    ) -> Dict[int, List[str]]:
        """Evaluates all webpages matched queries against the out_xpath provided by the resource.
        Outputs are transformed into their textual information (str).

        Args:
            resource (Resource): Resource to be evaluated
            queries (List[Query]): Given queries.

        Returns:
            Dict[int, List[str]]: Mapping from query_id to all retrieved outputs.
        """
        result = {}
        for q in queries:
            key_vals = []
            for wp in resource.webpages:
                for inp in wp.q_matches.get(q.id, []):
                    out_xpath = resource.out_xpath.as_xpath(start_node=inp)
                    eval_out = inp.xpath(out_xpath)
                    if eval_out:
                        key_vals.extend([element_str(e) for e in eval_out])
            result[q] = key_vals
        return result

    def _eval_wp_initial(
        self,
        webpage: WebPage,
        examples: List[Example],
        queries: List[Query],
        eval_func,
    ):
        """Evaluation of a single webpage. Input and output are evaluated. 
        Only if both values can be found, it is registered as a match.
        """

        def _eval_func(pairs, target: ElementTree, eval_func):
            matches = {}
            for pair in pairs:
                q_in, params_in, q_out, params_out = eval_func(pair)

                eval_inp = target.xpath(q_in, **params_in)
                if not eval_inp:
                    continue

                eval_out = []
                if isinstance(pair, Example):
                    eval_out = target.xpath(q_out, **params_out)
                    if not eval_out:
                        continue

                matches[pair.id] = {key: eval_out for key in eval_inp}
            return matches

        # raises etree.ParserError on bad formatted html
        # h = html.fromstring(webpage.html)
        # tree = etree.ElementTree(h)
        tree = etree.HTML(webpage.html)

        webpage.matches["true"] = _eval_func(examples, tree, eval_func)

        query_matches = _eval_func(queries, tree, eval_func)
        webpage.q_matches = {k: list(query_matches[k]) for k in query_matches}
