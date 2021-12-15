from enum import Enum
from typing import List

import numpy as np
from wrapping.objects.xpath.node import XPathNode

AXIS_DIFF_VAL = 1
PRED_DIFF_VAL = 1
NODETEST_DIFF_VAL = 2


class EDIT_ACTIONS(Enum):
    REPLACE = 0
    INSERT_0 = 1
    INSERT_1 = 2

def edit_distances(xpath_0: List[XPathNode], xpath_1: List[XPathNode]):
    distances = np.zeros((len(xpath_0) + 1, len(xpath_1) + 1))
    distances[:, 0] = np.arange(len(xpath_0) + 1) * sum(
        [AXIS_DIFF_VAL, PRED_DIFF_VAL, NODETEST_DIFF_VAL]
    )
    distances[0] = np.arange(len(xpath_1) + 1) * sum(
        [AXIS_DIFF_VAL, PRED_DIFF_VAL, NODETEST_DIFF_VAL]
    )
    for i in range(len(xpath_0)):
        idx_i = i + 1
        for j in range(len(xpath_1)):
            idx_j = j + 1
            step_0 = xpath_0[i]
            step_1 = xpath_1[j]

            dist_0 = min(distances[i, j], distances[idx_i, j], distances[i, idx_j])
            dist_1 = (
                (step_0.axisname != step_1.axisname) * AXIS_DIFF_VAL
                + (step_0.predicates != step_1.predicates) * PRED_DIFF_VAL
                + (step_0.nodetest != step_1.nodetest) * NODETEST_DIFF_VAL
            )
            distances[idx_i, idx_j] = dist_0 + dist_1
    return distances


def backtrack(distances: np.array, row: int = None, col: int = None):
    row = distances.shape[0] - 1 if row is None else row
    col = distances.shape[1] - 1 if col is None else col

    if row == 0 and col == 0:
        return []

    minval = distances[row, col]
    if col > 0:
        val = distances[row, col - 1]
        if val <= minval:
            argmin = (row, col - 1)
            action = EDIT_ACTIONS.INSERT_0
    if row > 0:
        val = distances[row - 1, col]
        if val <= minval:
            argmin = (row - 1, col)
            action = EDIT_ACTIONS.INSERT_1
    if row > 0 and col > 0:
        val = distances[row - 1, col - 1]
        argmin = (row - 1, col - 1)
        action = None
        # if val < minval:
        #     argmin = (row - 1, col - 1)
        #     action = EDIT_ACTIONS.REPLACE
        # elif val == minval:
        #     argmin = (row - 1, col - 1)
        #     action = None

    actions = backtrack(distances, *argmin)
    if action:
        actions.append((row, col, action))
    return actions


if __name__ == "__main__":
    edit_distances([0, 1, 2, 3], [0, 1])

