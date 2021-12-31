from collections import defaultdict
from math import isclose
from typing import Dict, List, Set, Tuple

import numpy as np
from db.queryGenerator import QueryExecutor
from wrapping.models.basic.evaluate import BasicEvaluator
from wrapping.models.nielandt.induce import NielandtInduction
from wrapping.models.nielandt.reduce import NielandtReducer
from wrapping.objects.pairs import Example, Query
from wrapping.objects.resource import Resource
from wrapping.tree.filter import TauMatchFilter
from wrapping.tree.uritree import group_uris

ALPHA = 0.99
PRIOR = 0.5
EPSILON = 1e-3


def expectation_maximization(examples: Set[Tuple[str, str]], queries: Set[str]):
    table_store = {}
    table_scores = {}
    answer_scores = {inp: {out: 1.0} for inp, out in examples}

    answers = examples
    finishedQuerying = False

    while True:
        answer_scores_old = answer_scores.copy()

        if not finishedQuerying:
            tables = queryForTables(
                answers,
                set(filter(lambda q: all(inp != q for inp, _ in answers), queries)),
            )
            print("\n".join(str(row) for table in tables.values() for row in table))
            oldX = len(answer_scores)
            updateLineage(tables, table_store, table_scores, answer_scores)
            newX = len(answer_scores)
            finishedQuerying = oldX == newX

        updateTableScores(table_store, table_scores, answer_scores)
        updateAnswerScores(table_store, table_scores, answer_scores, queries)

        answers = updateAnswers(answers, answer_scores)

        delta = score_diff(answer_scores_old, answer_scores)
        if finishedQuerying and delta < EPSILON:
            break

    result = dict(answers)
    for inp in queries:
        if inp not in result:
            result[inp] = None

    return set(result.items())


def queryForTables(
    examples: Set[Tuple[str, str]], queries: Set[str]
) -> Dict[str, Set[Tuple[str, str]]]:
    query_executor = QueryExecutor()
    resource_filter = TauMatchFilter(2)
    evaluator = BasicEvaluator()
    reducer = NielandtReducer()
    induction = NielandtInduction()

    examples = [Example(i, *ex) for i, ex in enumerate(examples)]
    queries = [Query(i + len(examples), q) for i, q in enumerate(queries)]
    pairs = examples + queries

    candidates = query_executor.get_uris_for(examples, queries)
    resource_groups = group_uris(candidates, resource_filter)

    tables = {}
    done = False
    for i in range(evaluator.TOTAL_EVALS):
        for resource in resource_groups:
            resource = Resource(*resource)
            evaluator.eval_initial(resource, pairs, i)

            reducer.reduce(resource)
            if not resource_filter.filter(resource.matched_examples(), set()):
                continue
            else:
                done = True

            induction.induce(resource, examples)

            table = evaluator.evaluate_query(resource, pairs)
            table = filter(lambda x: len(x[1]) == 1, table.items())
            table = set(map(lambda x: (x[0].inp, x[1][0]), table))
            tables[resource.id] = table
        if done:
            break
    return tables


def updateLineage(tables, table_store, table_scores, answer_scores):
    table_store.update(tables)

    for key, values in tables.items():
        if not key in table_scores:
            table_scores[key] = None

        for inp, out in values:
            if not inp in answer_scores:
                answer_scores[inp] = {out: 0}
            elif not out in answer_scores[inp]:
                answer_scores[inp][out] = 0


def updateTableScores(
    table_store, table_scores, answer_scores,
):
    def isMax(score, inp):
        # When all scores are the same, rounding errors might lead to wrong behaviour.
        return isclose(score, max(answer_scores[inp].values()))

    for key, table in table_store.items():
        good = 0
        bad = 0
        coveredX = set()
        for inp, out in table:
            coveredX.add(inp)
            score = answer_scores[inp][out]
            if isMax(score, inp):
                # if score == max(answer_scores[inp].values()):
                good += score
            else:
                bad += 1

        unseenX = 0
        for inp in set(answer_scores) - coveredX:
            unseenX += max(answer_scores[inp].values())

        table_scores[key] = (
            ALPHA * PRIOR * good / (PRIOR * good + (1 - PRIOR) * (bad + unseenX))
        )


def updateAnswerScores(table_store, table_scores, answer_scores, queries):
    for inp in set(queries) & set(answer_scores):
        # filtered_tables: All tables containing a transformation for 'inp'.
        filtered_tables = [
            (k, t) for k, t in table_store.items() if any(_inp == inp for _inp, _ in t)
        ]

        scoreOfNone = np.product([1 - table_scores[key] for key, _ in filtered_tables])
        scores = {}
        norm = scoreOfNone
        for out in answer_scores[inp]:
            out_val = np.product(
                [
                    abs(((inp, out) not in table) - table_scores[key])
                    for key, table in filtered_tables
                ]
            )
            scores[out] = out_val
            norm += out_val

        answer_scores[inp] = {k: v / norm for k, v in scores.items()}


def updateAnswers(answers, answer_scores):
    answers = set()
    for inp, values in answer_scores.items():
        argmax = None
        valmax = 0
        valnone = 1
        for key, val in values.items():
            valnone -= val
            if val > valmax:
                valmax = val
                argmax = key
        if valmax > valnone:
            answers.add((inp, argmax))
    return answers


def score_diff(answer_scores_old, answer_scores_new):
    return sum(
        [
            abs(
                answer_scores_new[inp][out] - answer_scores_old.get(inp, {}).get(out, 0)
            )
            for inp in answer_scores_new
            for out in answer_scores_new[inp]
        ]
    )
