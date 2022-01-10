from typing import List

import numpy as np
from wpdxf.wrapping.models.nielandt.utils import (EDIT_ACTIONS, backtrack,
                                                  edit_distance)
from wpdxf.wrapping.objects.xpath.node import XPathNode
from wpdxf.wrapping.objects.xpath.path import RelativeXPath, XPath


def align(xpaths: List[XPath]) -> List[XPath]:
    # Choose pair of xpaths with minimal distance between each other.
    min_cost = (np.array([[np.inf]]),)
    for i, xpath0 in enumerate(xpaths):
        for xpath1 in xpaths[i + 1 :]:
            edit_matrix = edit_distance(xpath0, xpath1)
            if edit_matrix[-1, -1] < min_cost[0][-1, -1]:
                min_cost = (edit_matrix, xpath0, xpath1)
    edit_matrix, xpath0, xpath1 = min_cost

    aligned_xpaths = align_new_path(
        backtrack(edit_matrix, xpath0, xpath1), xpath0, [xpath1]
    )
    xpaths.remove(xpath0)
    xpaths.remove(xpath1)

    # Iteratively align new path with minimal mean costs.
    while xpaths:
        min_cost = (np.array([[np.inf]]),)
        for xpath0 in xpaths:
            xpath_mean = []
            for xpath1 in aligned_xpaths:
                edit_matrix = edit_distance(xpath0, xpath1)
                xpath_mean.append(edit_matrix[-1, -1])
            mean_cost = np.mean(xpath_mean)
            if mean_cost < min_cost[0]:
                min_cost = (mean_cost, edit_matrix, xpath0, xpath1)
        _, edit_matrix, xpath0, xpath1 = min_cost
        xpaths.remove(xpath0)
        aligned_xpaths = align_new_path(
            backtrack(edit_matrix, xpath0, xpath1), xpath0, aligned_xpaths
        )

    assert all(map(lambda x: len(x) == len(aligned_xpaths[0]), aligned_xpaths))

    return aligned_xpaths


def align_new_path(
    actions: List[EDIT_ACTIONS], xpath_0: XPath, xpaths: List[XPath]
) -> List[XPath]:
    off_0, off_1 = 0, 0
    for step_idx0, step_idx1, action in actions:
        if action is EDIT_ACTIONS.INSERT_0:
            xpath_0.insert(off_0 + step_idx0, XPathNode.new_self())
            off_0 += 1
        elif action is EDIT_ACTIONS.INSERT_1:
            for xpath in xpaths:
                xpath.insert(off_1 + step_idx1, XPathNode.new_self())
            off_1 += 1

    assert len(xpaths[0]) == len(xpath_0), f"{','.join([str(xp) for xp in xpaths])}\n{xpath_0}\n{actions}"
    return xpaths + [xpath_0]
