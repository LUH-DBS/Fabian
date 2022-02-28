from copy import deepcopy
from typing import List, Set, Tuple

from lxml.etree import _Element
from wpdxf.wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wpdxf.wrapping.objects.xpath.path import RelativeXPath, XPath, nodelist
from wpdxf.wrapping.objects.xpath.predicate import (AttributePredicate,
                                                    Predicate)


def preprocess(
    xpath_g: XPath, element_pairs: List[Tuple[_Element, _Element]], prefix: XPath = None
):
    result = []

    for i in range(len(xpath_g)):
        indicated_nodes = set()
        overflow_nodes = set()

        # start_path remains unchanged for all pairs
        start_path = xpath_g[i + 1 :]
        start_path.insert(0, XPathNode.self_node())
        start_path, _ = start_path.xpath()

        for c_element, e_element in element_pairs:
            ind_xpath = e_element.getroottree().getpath(e_element)

            # common_path must be a shallow copy for each element pair, as the end_node is appended.
            common_path = xpath_g[:i]
            if prefix:
                common_path = prefix + common_path

            # end_node (end_node's predicate) changes for each pair,
            # deepcopy avoids unintended manipulation of original data.
            end_node = deepcopy(xpath_g[i])
            end_node.add_predicate(left=start_path, right=ind_xpath)

            common_path.append(end_node)
            xpath, cvars = common_path.xpath()

            nodes = set(nodelist(end=e_element))
            eval_out = set(c_element.xpath(xpath, **cvars))

            # Add all indicated/overflow nodes.
            indicated_nodes |= eval_out & nodes
            overflow_nodes |= eval_out - nodes
            # Remove (now indicated) overflow nodes,
            # if they were added in an earlier iteration.
            overflow_nodes -= indicated_nodes

        result.append((indicated_nodes, overflow_nodes))

    return result


def enrich(xpath: XPath, node_list: list):
    for step, (indicated_nodes, overflow_nodes) in zip(xpath, node_list):
        # if overflow_nodes:
        enrich_step(step, indicated_nodes, overflow_nodes)
    return xpath


def enrich_step(
    step: XPathNode, indicated_nodes: Set[_Element], overflow_nodes: Set[_Element],
):
    for enrich_func in __ENRICHMENT_FUNC__:
        enrich_func(step, indicated_nodes, overflow_nodes)


def _preceding_sibling(step, indicated_nodes, overflow_nodes):
    # Collect tags of preceding siblings that occurs for all indicated nodes of a step,
    # but not for a single overflow node.

    def collect(element: _Element):
        return set(e.tag for e in element.xpath("preceding-sibling::*"))

    if len(indicated_nodes) < 1:
        return

    indicated_tags = set.intersection(*map(collect, indicated_nodes))
    overflow_tags = (
        set.union(*map(collect, overflow_nodes)) if overflow_nodes else set()
    )
    common_tags = indicated_tags - overflow_tags

    [step.add_predicate(left=f"preceding-sibling::{tag}") for tag in common_tags]


def _similar_attributes(step, indicated_nodes, overflow_nodes):
    # Find attributes that exist for all indicated nodes.
    # If the key-value pair is the same, check for equality.
    # Otherwise, check for key existance.
    if len(indicated_nodes) < 1 or any(
        not isinstance(node, _Element) for node in indicated_nodes
    ):
        return

    similar_attributes = []

    eq_keys = set.intersection(*(set(node.attrib) for node in indicated_nodes))
    for key in eq_keys:
        ind_nodes_list = list(indicated_nodes)
        value = ind_nodes_list[0].attrib[key]
        if all(node.attrib[key] == value for node in ind_nodes_list[1:]):
            similar_attributes.append((key, value))
        else:
            similar_attributes.append((key, None))

    print("Similar attributes:", similar_attributes)
    [step.add_attribute(left, right=right) for left, right in similar_attributes]


def _node_names(step, indicated_nodes, overflow_nodes):
    # Reduce the expressivity of an arbitrary 'node()' also '*'
    # by adding a disjunction of all indicated nodetests.
    if not overflow_nodes or any(
        not isinstance(node, _Element) for node in indicated_nodes
    ):
        return

    indicated_names = set(node.tag for node in indicated_nodes)
    overflow_names = set(node.tag for node in overflow_nodes)
    if not (indicated_names & overflow_names):
        step.predicates.append([Predicate(f"self::{nt}" for nt in indicated_names)])
    else:
        # Integer check
        indicated_int_nodes = list(
            filter(
                lambda n: n.xpath(
                    "self::*[re:test(text(), '^\d+$')]",
                    namespaces={"re": "http://exslt.org/regular-expressions"},
                ),
                indicated_nodes,
            )
        )
        overflow_int_nodes = list(
            filter(
                lambda n: n.xpath(
                    "self::*[re:test(text(), '^\d+$')]",
                    namespaces={"re": "http://exslt.org/regular-expressions"},
                ),
                indicated_nodes,
            )
        )
        if (
            len(indicated_int_nodes) == len(indicated_nodes)
            and len(overflow_int_nodes) == 0
        ):
            step.add_predicate("re:test(text(), '^\d+$')")


def _close_neighbours(step, indicated_nodes, overflow_nodes):
    def _collect(nodes: List[_Element], path: XPath):
        text_dict = None
        for node in nodes:
            neighbours = node.xpath(str(path))
            if text_dict is None:
                text_dict = {
                    text: set([(n.tag, i + 1)])
                    for n in neighbours
                    for i, text in enumerate(n.xpath("text()"))
                }
            else:
                new_text_dict = {
                    text: set([(n.tag, i + 1)])
                    for n in neighbours
                    for i, text in enumerate(n.xpath("text()"))
                }
                new_keys = set(text_dict) & set(new_text_dict)

                text_dict = {
                    key: text_dict[key] | new_text_dict[key] for key in new_keys
                }
                if not text_dict:
                    break
        return text_dict

    if len(indicated_nodes) < 2 or len(overflow_nodes) < 2:
        return

    # Nephews:
    path = XPath(
        [
            XPathNode.self_node(),
            XPathNode(axisname=AXISNAMES.PAR),
            XPathNode(axisname=AXISNAMES.PSIB),  # PSIB
        ]
    )
    indicated_td = _collect(indicated_nodes, path)
    overflow_td = _collect(overflow_nodes, path)

    for key in indicated_td:
        if key in overflow_td:
            break
        key_path = deepcopy(path)
        key_path.append(XPathNode(nodetest="text()"))

        if len(indicated_td[key]) == 1:
            tag, position = list(indicated_td[key])[0]
            key_path[-2].nodetest = tag
            key_path[-1].add_predicate("position()", right=position)
        kpath, kvars = key_path.xpath()
        step.add_predicate(left=f"{kpath}='{key}'", variables=kvars)

    path = XPath(
        [
            XPathNode.self_node(),
            XPathNode(axisname=AXISNAMES.PAR),
            XPathNode(axisname=AXISNAMES.FSIB),  # FSIB
        ]
    )
    indicated_td = _collect(indicated_nodes, path)
    overflow_td = _collect(overflow_nodes, path)

    for key in indicated_td:
        if key in overflow_td:
            break
        key_path = deepcopy(path)
        key_path.append(XPathNode(nodetest="text()"))

        if len(indicated_td[key]) == 1:
            tag, position = list(indicated_td[key])[0]
            key_path[-2].nodetest = tag
            key_path[-1].add_predicate("position()", right=position)
        kpath, kvars = key_path.xpath()
        step.add_predicate(left=f"{kpath}='{key}'", variables=kvars)


def _common_prefixes(step, indicated_nodes, overflow_nodes):
    indicated_strings = [node.xpath("text()") for node in indicated_nodes]

    lcp = ""  # Longest Common Prefix
    for i in range(min([len(s) for s in indicated_strings])):
        c = indicated_strings[0][i]
        if all(s[i] == c for s in indicated_strings):
            lcp += c
        else:
            break

    if lcp:
        step.add_predicate(f"starts-with(text(), $lcp)", variables={"lcp": lcp})


def _neighbourhood_search(step, indicated_nodes, overflow_nodes):
    ...


__ENRICHMENT_FUNC__ = (
    _preceding_sibling,
    _similar_attributes,
    _node_names,
    _common_prefixes,
)
# _close_neighbours not finished!
# _neighbourhood search not implemented

