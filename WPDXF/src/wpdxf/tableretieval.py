from DataXFormer.data.Answer import Answer
from DataXFormer.data.DBUtil import DBUtil



from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.models.nielandt.induce import NielandtInduction
from wpdxf.wrapping.models.nielandt.reduce import NielandtReducer
from wpdxf.wrapping.tree.filter import TauMatchFilter
from wpdxf.wrapping.wrapper import wrap


class WebPageRetrieval:
    def __init__(self) -> None:
        self.query_executor = QueryExecutor()

        self.resource_filter = TauMatchFilter
        self.evaluation = BasicEvaluator()
        self.reduction = NielandtReducer()
        self.induction = NielandtInduction()

    def run(self, examples, queries, tau=2):
        resource_filter = self.resource_filter(tau)

        # examples = list(zip([v[0] for v in examples[0]], [v[0] for v in examples[1]]))
        examples = [(x[0], y[0]) for x, y in examples]
        queries = [v[0] for (v,) in queries]

        tables = wrap(
            examples,
            queries,
            self.query_executor,
            resource_filter,
            self.evaluation,
            self.reduction,
            self.induction,
        )

        reversedQS = {}
        for key, table in tables.items():
            reversedQS[key] = {
                "content": list(table),
                "confidence": 0,
                "openrank": 0,
                "colid": [0, 1],
            }

        EX = set([x for x, _ in examples])
        Q = queries
        exampleAnswerList = []
        answerList = []
        for key, table in tables.items():
            for x, y in table:
                if x in EX:
                    exampleAnswerList.append(Answer(x, y, key, isExample=True))
                elif x in Q:
                    answerList.append(Answer(x, y, key))
        return exampleAnswerList, answerList, Q, reversedQS


class WebTableRetrieval:
    def run(self, examples, queries, tau=2):
        from DataXFormer.webtableindexer.Tokenizer import Tokenizer
        from DataXFormer.webtables.TableScore import TableScorer
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
        from flashextract.synthesize import ExtractionProgSynthesizer#, FlashExtractReduction
        self.induction = ExtractionProgSynthesizer()
        #self.reduction = FlashExtractReduction()