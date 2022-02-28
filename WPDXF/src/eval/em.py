from copy import deepcopy
from typing import Dict, List, Set, Tuple

import numpy as np

from eval.sources import Source


def is_max(score: float, inp: str, answers) -> bool:
    if score == max(answers[inp].values()):
        return True
    return False


def get_answers(answer_scores: Dict[str, Dict[str, float]]) -> List[Tuple[str, str]]:
    answers = []
    for inp, outs in answer_scores.items():
        if not outs:
            continue

        vals, scores = zip(*outs.items())
        idx = np.argmax(scores)

        if (1 - sum(scores)) < scores[idx]:
            answers.append((inp, vals[idx]))

    return answers


class TableScorer:
    _alpha = 0.99
    _epsilon = 1e-3
    _max_iter = 100

    def __init__(
        self,
        source: Source,
        alpha: float = None,
        epsilon: float = None,
        max_iter: int = None,
    ) -> None:
        self.source = source

        self.table_scores: Dict[str, float] = {}
        self.answer_scores: Dict[str, Dict[str, float]] = {}

        self.alpha = alpha or self._alpha
        self.epsilon = epsilon or self._epsilon
        self.max_iter = max_iter or self._max_iter

    def update_table_scores(self, tables):
        for tid, table in tables.items():
            good = 0
            bad = 0
            uncovered_X = set([k for k, v in self.answer_scores.items() if len(v) > 0])
            for inp, out in table:
                uncovered_X.remove(inp)

                score = self.answer_scores[inp][out]
                if is_max(score, inp, self.answer_scores):
                    good += score
                else:
                    bad += 1
            unseen_X = sum(
                [max(self.answer_scores[inp].values()) for inp in uncovered_X]
            )
            prior = 0.5

            new_score = (prior * good) / (prior * good + (1 - prior) * (bad + unseen_X))
            self.table_scores[tid] = self.alpha * new_score

    def update_answer_scores(self, tables, queries):
        for inp in queries:
            score_of_none = 1.0
            for tid, table in tables.items():
                table_score = self.table_scores[tid]

                table_answer = None
                for _inp, _out in table:
                    if _inp == inp:
                        table_answer = _out

                if table_answer is None:
                    continue
                score_of_none *= 1 - table_score

                for out, score in self.answer_scores[inp].items():
                    if score == 0.0:
                        _score = 1.0
                    else:
                        _score = score

                    if table_answer == out:
                        self.answer_scores[inp][out] = _score * table_score
                    else:
                        self.answer_scores[inp][out] = _score * (1 - table_score)

            _sum = sum(self.answer_scores[inp].values()) + score_of_none
            for out in self.answer_scores[inp]:
                self.answer_scores[inp][out] /= _sum

    def expectation_maximization(
        self, examples: Set[Tuple[str, str]], queries: Set[str],
    ):
        iter = 0

        inp_vals = set(map(lambda ex: ex[0], examples)) | queries

        self.answer_scores = {inp: {out: 1.0} for inp, out in examples}
        self.answer_scores.update({q: {} for q in queries})

        self.table_scores = {}

        finishedQuerying = False
        old_answers = deepcopy(self.answer_scores)
        while True:
            if not finishedQuerying:
                finishedQuerying = True

                _answers = get_answers(self.answer_scores)
                _queries = queries - set(map(lambda ex: ex[0], _answers))
                _tables = self.source.query_tables(_answers, _queries)

                tables: Dict[str, List[Tuple[str, str]]] = {}
                for tid, _table in _tables.items():
                    table = []
                    for inp, out in _table:
                        if inp in inp_vals:
                            table.append((inp, out))
                            if inp in queries and out not in self.answer_scores[inp]:
                                self.answer_scores[inp][out] = 0.0
                                finishedQuerying = False

                    tables[tid] = table

            self.update_table_scores(tables)
            self.update_answer_scores(tables, queries)

            delta_score = 0
            for inp, outs in self.answer_scores.items():
                for out, score in outs.items():
                    old_score = old_answers.get(inp, {}).get(out, 0.0)
                    delta_score += abs(score - old_score)

            print("Iteration:", iter)
            print("Answer scores:", self.answer_scores)
            print("Table scores:", self.table_scores)
            print("Delta", delta_score)

            if (
                finishedQuerying and delta_score < self.epsilon
            ) or iter > self.max_iter:
                break

            old_answers = deepcopy(self.answer_scores)
            iter += 1

        return self.answer_scores

# if __name__ == "__main__":
#     from eval.sources import WebTableSource, WebPageSource
#     from DataXFormer.webtableindexer.Tokenizer import Tokenizer
#     from eval.sources import WebPageSource, WebTableSource
#     examples = {("Spain", "Spanish"), ("Germany", "German"), ("England", "English")}
#     queries = {"Denmark", "France"}
#     scorer = TableScorer(WebPageSource())
#     aw = scorer.expectation_maximization(examples, queries)
#     print(get_answers(aw))
