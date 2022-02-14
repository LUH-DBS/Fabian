from DataXFormer.data.Answer import Answer
from DataXFormer.data.DBUtil import DBUtil
from DataXFormer.webtableindexer.Tokenizer import Tokenizer
from DataXFormer.webtables.TableScore import TableScorer

from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.models.nielandt.induce import NielandtInduction
from wpdxf.wrapping.models.nielandt.reduce import NielandtReducer
from wpdxf.wrapping.wrapper import wrap


class WebPageRetrieval:
    def __init__(self) -> None:
        self.query_executor = QueryExecutor()

        self.evaluation = BasicEvaluator()
        self.reduction = NielandtReducer()
        self.induction = NielandtInduction()

    def run(self, examples, queries, tau=2):

        examples = [(x[0], y[0]) for x, y in examples]
        queries = [v[0] for (v,) in queries]
        tables = wrap(
            examples,
            queries,
            self.query_executor,
            tau,
            self.evaluation,
            self.reduction,
            self.induction,
        )

        tokenizer = Tokenizer()

        reversedQS = {}
        for key, table in tables.items():
            table = [
                (tokenizer.tokenize(inp), tokenizer.tokenize(out)) for inp, out in table
            ]
            reversedQS[key] = {
                "content": table,
                "confidence": 0,
                "openrank": 0,
                "colid": [0, 1],
            }

        Q = set(tokenizer.tokenize(q) for q in queries)
        EX = set(
            (tokenizer.tokenize(inp), tokenizer.tokenize(out)) for inp, out in examples
        )
        exampleAnswerList = []
        answerList = []
        for key, values in reversedQS.items():
            for x, y in values["content"]:
                if x in Q:
                    answerList.append(Answer(x, y, key))
                if (x, y) in EX:
                    exampleAnswerList.append(Answer(x, y, key, isExample=True))
        return exampleAnswerList, answerList, Q, reversedQS


class WebTableRetrieval:
    def run(self, examples, queries, tau=2):
        from DataXFormer.webtables.Transformer import DirectTransformer

        tableLimit = None

        tokenizer = Tokenizer()
        dbUtil = DBUtil("postgres")
        dt = DirectTransformer()
        scorer = TableScorer()

        def _transform(l: list, idx: int):
            return [tokenizer.tokenize(x[idx][0]) for x in l]

        XList = _transform(examples, 0)
        Y = _transform(examples, 1)
        Q = _transform(queries, 0)

        qs = dbUtil.queryWebTables(XList, Y, tau)

        queriedTableList = [*set([t for t, *_ in qs])]
        if tableLimit is not None:
            queriedTableList = queriedTableList[:tableLimit]
            qs = [x for x in qs if x[0] in queriedTableList]

        if queriedTableList:
            reversedQS = dbUtil.reverseQuery(XList, Y, queriedTableList)
        else:
            reversedQS = {}

        valid = dbUtil.findValidTable(XList, Y)
        validTable = dt.validateTable(qs, valid)

        qs = [x for x in qs if x[0] in validTable]

        answerList, _ = dt.transform(XList, Y, Q, reversedQS, queriedTableList)
        exampleAnswerList = scorer.exampleListToAnswer([*zip(XList, Y)], reversedQS)

        return exampleAnswerList, answerList, Q, reversedQS


class FlashExtractRetrieval(WebPageRetrieval):
    def __init__(self) -> None:
        super().__init__()
        from flashextract.synthesize import \
            ExtractionProgSynthesizer  # , FlashExtractReduction

        self.induction = ExtractionProgSynthesizer()
        # self.reduction = FlashExtractReduction()

