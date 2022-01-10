from enum import Enum

import numpy as np
from wpdxf.wrapping.objects.xpath.node import XPathNode
from wpdxf.wrapping.objects.xpath.path import XPath

AXIS_DIFF_VAL = 1
PRED_DIFF_VAL = 1
NODETEST_DIFF_VAL = 2


class EDIT_ACTIONS(Enum):
    REPLACE = 0
    INSERT_0 = 1
    INSERT_1 = 2


def replace_cost(step0: XPathNode, step1: XPathNode):
    return (
        (step0.axisname != step1.axisname) * AXIS_DIFF_VAL
        + (step0.predicates != step1.predicates) * PRED_DIFF_VAL
        + (step0.nodetest != step1.nodetest) * NODETEST_DIFF_VAL
    )


def edit_distance(xpath0: XPath, xpath1: XPath):
    distances = np.zeros((len(xpath0) + 1, len(xpath1) + 1))
    insert_cost = sum([AXIS_DIFF_VAL, PRED_DIFF_VAL, NODETEST_DIFF_VAL])
    distances[:, 0] = np.arange(len(xpath0) + 1) * insert_cost
    distances[0, :] = np.arange(len(xpath1) + 1) * insert_cost

    for i in range(len(xpath0)):
        idx_i = i + 1
        for j in range(len(xpath1)):
            idx_j = j + 1
            distances[idx_i, idx_j] = min(
                distances[i, idx_j] + insert_cost,
                distances[idx_i, j] + insert_cost,
                distances[i, j] + replace_cost(xpath0[i], xpath1[j]),
            )
    return distances


def backtrack(distances: np.array, xpath0: XPath, xpath1: XPath):
    actions = []
    insert_cost = sum([AXIS_DIFF_VAL, PRED_DIFF_VAL, NODETEST_DIFF_VAL])
    row = distances.shape[0] - 1
    col = distances.shape[1] - 1

    while row > 0 and col > 0:
        value = distances[row, col]
        if value == distances[row - 1, col - 1] + replace_cost(
            xpath0[row - 1], xpath1[col - 1]
        ):
            action = None
            row -= 1
            col -= 1
        elif value == distances[row, col - 1] + insert_cost:
            action = EDIT_ACTIONS.INSERT_0
            col -= 1
        else:  # if value == distances[row - 1, col] + insert_cost:
            action = EDIT_ACTIONS.INSERT_1
            row -= 1
        if action is not None:
            actions.append((row, col, action))

    while row > 0:
        actions.append((row, col, EDIT_ACTIONS.INSERT_1))
        row -= 1
    while col > 0:
        actions.append((row, col, EDIT_ACTIONS.INSERT_0))
        col -= 1

    assert abs(len(xpath0) - len(xpath1)) == len(actions), f"{xpath0} {xpath1}\n{actions}\n{distances}"
    return actions[::-1]
