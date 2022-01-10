from copy import deepcopy
from typing import List, Set

from lxml.etree import ElementBase
from wpdxf.wrapping.objects.xpath.node import AXISNAMES, XPathNode
from wpdxf.wrapping.objects.xpath.path import RelativeXPath, XPath, nodelist
from wpdxf.wrapping.objects.xpath.predicate import (AttributePredicate,
                                                    Conjunction, Disjunction,
                                                    Predicate)


def preprocess_startpath(xpath_g: XPath, xpaths: List[RelativeXPath]):
    result = []

    for i in range(len(xpath_g)):
        indicated_nodes = set()
        overflow_nodes = set()

        start_path = xpath_g[i + 1 :]
        for xpath in xpaths:
            common_path = xpath.common_path + xpath_g[:i]
            end_path = xpath_g[i : i + 1]

            xp = RelativeXPath(
                common_path=common_path,
                start_path=start_path,
                start_node=xpath.start_node,
                end_node=None,
                end_path=end_path,
            )
            nodes = set(nodelist(xpath.start_node))
            eval_out = set(xpath.start_node.xpath(str(xp)))

            # Add all indicated/overflow nodes.
            indicated_nodes |= eval_out & nodes
            overflow_nodes |= eval_out - nodes
            # Remove (now indicated) overflow nodes,
            # if they were added in an earlier iteration.
            overflow_nodes -= indicated_nodes

        # print("Indicated Nodes:")
        # for n in indicated_nodes:
        #     print(n, n.getroottree().getpath(n))
        # print("Overflow Nodes:")
        # for n in overflow_nodes:
        #     print(n, n.getroottree().getpath(n))
        result.append((indicated_nodes, overflow_nodes))

    return result


def preprocess_fullpath(xpath_g: RelativeXPath, xpaths: List[RelativeXPath]):
    result = []

    max_range = len(xpath_g.full_path(abs_start_path="$input")[1])

    for i in range(max_range):
        indicated_nodes = set()
        overflow_nodes = set()

        for xpath in xpaths:
            _, xpg = xpath_g.full_path(xpath.start_node)
            start_path = xpg[i + 1 :]
            common_path = xpath.common_path + xpg[:i]
            end_path = xpg[i : i + 1]

            xp = RelativeXPath(
                common_path=common_path,
                start_path=start_path,
                start_node=xpath.end_node,
                end_node=None,
                end_path=end_path,
            )
            nodes = set(nodelist(xpath.end_node))
            eval_out = set(xpath.end_node.xpath(str(xp)))

            # Add all indicated/overflow nodes.
            indicated_nodes |= eval_out & nodes
            overflow_nodes |= eval_out - nodes
            # Remove (now indicated) overflow nodes,
            # if they were added in an earlier iteration.
            overflow_nodes -= indicated_nodes

        # print("Indicated Nodes:")
        # for n in indicated_nodes:
        #     print(n, n.getroottree().getpath(n))
        # print("Overflow Nodes:")
        # for n in overflow_nodes:
        #     print(n, n.getroottree().getpath(n))
        result.append((indicated_nodes, overflow_nodes))

    return result


def enrich(xpath: XPath, node_list: list):
    for step, (indicated_nodes, overflow_nodes) in zip(xpath, node_list):
        # if overflow_nodes:
        enrich_step(step, indicated_nodes, overflow_nodes)
    return xpath


def enrich_step(
    step: XPathNode,
    indicated_nodes: Set[ElementBase],
    overflow_nodes: Set[ElementBase],
):
    for enrich_func in __ENRICHMENT_FUNC__:
        enrich_func(step, indicated_nodes, overflow_nodes)


def _preceding_sibling(step, indicated_nodes, overflow_nodes):
    # Collect tags of preceding siblings that occurs for all indicated nodes of a step,
    # but not for a single overflow node.

    def collect(element: ElementBase):
        return set(e.tag for e in element.xpath("preceding-sibling::*"))

    indicated_tags = set.intersection(*map(collect, indicated_nodes))
    overflow_tags = (
        set.union(*map(collect, overflow_nodes)) if overflow_nodes else set()
    )
    common_tags = indicated_tags - overflow_tags

    step.predicates.extend(
        [Predicate(f"preceding-sibling::{tag}") for tag in common_tags]
    )


def _similar_attributes(step, indicated_nodes, overflow_nodes):
    # Find attributes that exist for all indicated nodes.
    # If the key-value pair is the same, check for equality.
    # Otherwise, check for key existance.
    similar_attributes = []

    eq_keys = set.intersection(*(set(node.attrib) for node in indicated_nodes))
    for key in eq_keys:
        ind_nodes_list = list(indicated_nodes)
        value = ind_nodes_list[0].attrib[key]
        if all(node.attrib[key] == value for node in ind_nodes_list[1:]):
            similar_attributes.append((key, value))
        else:
            similar_attributes.append((key, None))

    step.predicates.extend(
        AttributePredicate(left, right=right) for left, right in similar_attributes
    )


def _node_names(step, indicated_nodes, overflow_nodes):
    # Reduce the expressivity of an arbitrary 'node()' also '*'
    # by adding a disjunction of all indicated nodetests.
    if not overflow_nodes:
        return

    indicated_names = set(node.tag for node in indicated_nodes)
    overflow_names = set(node.tag for node in overflow_nodes)
    if not (indicated_names & overflow_names):
        step.predicates.append(
            Disjunction(Predicate(f"self::{nt}") for nt in indicated_names)
        )
    # TODO: Integer check is ignored for now.


def _close_neighbours(step, indicated_nodes, overflow_nodes):
    def _collect(nodes: List[ElementBase], path: XPath):
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
            XPathNode.new_self(),
            XPathNode(axisname=AXISNAMES.PAR),
            XPathNode(axisname=AXISNAMES.PSIB),
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
            key_path[-1].predicates.append(Predicate("position()", right=position))
        step.predicates.append(Predicate(left=f"{key_path}='{key}'"))

    path = XPath(
        [
            XPathNode.new_self(),
            XPathNode(axisname=AXISNAMES.PAR),
            XPathNode(axisname=AXISNAMES.FSIB),
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
            key_path[-1].predicates.append(Predicate("position()", right=position))
        step.predicates.append(Predicate(left=f"{key_path}='{key}'"))


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
        step.predicates.append(Predicate(f'starts-with(., "{lcp}")'))


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

