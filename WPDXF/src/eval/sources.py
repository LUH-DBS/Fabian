from collections import defaultdict
from typing import Dict, Set, Tuple

from DataXFormer.data.DBUtil import DBUtil
from DataXFormer.webtableindexer.Tokenizer import Tokenizer
from DataXFormer.webtables.TableScore import TableScorer
from DataXFormer.webtables.Transformer import DirectTransformer
from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.models.nielandt.induce import NielandtInduction
from wpdxf.wrapping.models.nielandt.reduce import NielandtReducer
from wpdxf.wrapping.objects.pairs import tokenized
from wpdxf.wrapping.wrapper import wrap


class Source:
    def __init__(self, tau: int = 2) -> None:
        self.tau = tau
        self.cache = {}

    def prepare_input(
        self,
        examples: Set[Tuple[str, str]],
        queries: Set[str],
        groundtruth: Set[Tuple[str, str]],
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        return examples, queries, groundtruth

    def prepare_output(
        self,
        examples: Set[Tuple[str, str]],
        answers: Set[Tuple[str, str]],
        groundtruth: Set[Tuple[str, str]],
    ):
        return examples, answers, groundtruth

    def query_tables(
        self, examples: Set[Tuple[str, str]], queries: Set[str]
    ) -> Dict[str, Set[Tuple[str, str]]]:
        cache_key = tuple(sorted(examples)), tuple(sorted(queries))

        if cache_key in self.cache:
            result = self.cache[cache_key]
        else:
            result = self._query_tables(examples, queries)
            self.cache[cache_key] = result
        return result

    def _query_tables(
        self, examples: Set[Tuple[str, str]], queries: Set[str]
    ) -> Dict[str, Set[Tuple[str, str]]]:
        ...


class WebTableSource(Source):
    def __init__(self, tau: int = 2, table_limit: int = None) -> None:
        super().__init__(tau)

        self.table_limit = table_limit

        self.dbutil = DBUtil("postgres")
        self.tokenizer = Tokenizer()
        self.dt = DirectTransformer()
        self.scorer = TableScorer()

    def prepare_input(
        self,
        examples: Set[Tuple[str, str]],
        queries: Set[str],
        groundtruth: Set[Tuple[str, str]],
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:
        X, Y = zip(*examples)
        X = [*map(self.tokenizer.tokenize, X)]
        Y = [*map(self.tokenizer.tokenize, Y)]
        examples = set(zip(X, Y))

        queries = set(map(self.tokenizer.tokenize, queries))

        X, Y = zip(*groundtruth)
        X = [*map(self.tokenizer.tokenize, X)]
        Y = [*map(self.tokenizer.tokenize, Y)]
        groundtruth = set(zip(X, Y))

        return examples, queries, groundtruth

    def _query_tables(
        self, examples: Set[Tuple[str, str]], queries: Set[str]
    ) -> Dict[str, Set[Tuple[str, str]]]:
        X, Y = zip(*examples)
        qs = self.dbutil.queryWebTables(X, Y, self.tau)

        queriedTableList = [*set([t for t, *_ in qs])]
        if self.table_limit is not None:
            queriedTableList = queriedTableList[: self.table_limit]
            qs = [x for x in qs if x[0] in queriedTableList]

        if queriedTableList:
            reversedQS = self.dbutil.reverseQuery(X, Y, queriedTableList)
        else:
            reversedQS = {}

        valid = self.dbutil.findValidTable(X, Y)
        validTable = self.dt.validateTable(qs, valid)
        qs = [x for x in qs if x[0] in validTable]

        answerList, _ = self.dt.transform(X, Y, queries, reversedQS, queriedTableList)
        exampleAnswerList = self.scorer.exampleListToAnswer([*zip(X, Y)], reversedQS)

        # Transform answer to Dict format
        tables = defaultdict(set)
        for answer in answerList + exampleAnswerList:
            tables[answer.tableid].add((answer.X, answer.Y))

        return dict(tables)


class WebPageSource(Source):
    def __init__(self, tau: int = 2, enrich_predicates: bool = True) -> None:
        super().__init__(tau)
        self.query_executor = QueryExecutor()
        self.evaluation = BasicEvaluator()
        self.reduction = NielandtReducer()
        self.induction = NielandtInduction(enrich_predicates=enrich_predicates)

    def prepare_input(
        self,
        examples: Set[Tuple[str, str]],
        queries: Set[str],
        groundtruth: Set[Tuple[str, str]],
    ) -> Tuple[Set[Tuple[str, str]], Set[str]]:

        examples = set([tokenized(*ex) for ex in examples])
        queries = set([tokenized(q) for q in queries])

        groundtruth = set([tokenized(*gt) for gt in groundtruth])

        return examples, queries, groundtruth

    def _query_tables(
        self, examples: Set[Tuple[str, str]], queries: Set[str]
    ) -> Dict[str, Set[Tuple[str, str]]]:
        tables = wrap(
            examples,
            queries,
            self.query_executor,
            self.tau,
            self.evaluation,
            self.reduction,
            self.induction,
        )
        return tables
