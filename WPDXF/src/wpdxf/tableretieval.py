from dataXFormer.data.Answer import Answer
from dataXFormer.data.DBUtil import DBUtil, getDBUtil

from wpdxf.db.queryGenerator import QueryExecutor
from wpdxf.wrapping.wrapper import wrap


class WebPageRetrieval:
    def __init__(self, resource_filter, evaluation, reduction, induction) -> None:
        self.query_executor = QueryExecutor()

        self.resource_filter = resource_filter
        self.evaluation = evaluation
        self.reduction = reduction
        self.induction = induction

    def run(self, examples, queries):
        examples = list(zip([v[0] for v in examples[0]], [v[0] for v in examples[1]]))
        queries = [v[0] for v in queries[0]]
        tables = wrap(
            examples,
            queries,
            self.query_executor,
            self.resource_filter,
            self.evaluation,
            self.reduction,
            self.induction,
        )
        for key, table in tables.items():
            print(key)
            for row in table:
                print(row)

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
    def run(self, examples, queries):
        from dataXFormer.webtableindexer.Tokenizer import Tokenizer
        from dataXFormer.webtables.TableScore import TableScorer
        from dataXFormer.webtables.Transformer import DirectTransformer

        tau = 2
        tableLimit = None

        tokenizer = Tokenizer()
        dbUtil = getDBUtil("postgres")
        dt = DirectTransformer()
        scorer = TableScorer()

        def _transform(l: list):
            return [tokenizer.tokenize(x[0]) for x in l]

        ex_X = [x for (x,) in examples[0]]
        ex_Y = [x for (x,) in examples[1]]
        qu_X = [x for (x,) in queries[0]]

        XList = [*map(tokenizer.tokenize, ex_X)]
        Y = [*map(tokenizer.tokenize, ex_Y)]
        Q = [*map(tokenizer.tokenize, qu_X)]

        XList_map = dict(zip(XList, ex_X))
        Y_map = dict(zip(Y, ex_Y))
        Q_map = dict(zip(Q, qu_X))

        qs = dbUtil.queryWebTables(XList, Y, tau)

        queriedTableList = [*set([t for t, *_ in qs])]
        if tableLimit is not None:
            queriedTableList = queriedTableList[:tableLimit]
            qs = [x for x in qs if x[0] in queriedTableList]

        reversedQS = self.reverseQuery(
            XList, Y, queriedTableList
        )  # dbUtil.reverseQuery(XList, Y, queriedTableList)

        valid = dbUtil.findValidTable(XList, Y)
        validTable = dt.validateTable(qs, valid)

        qs = [x for x in qs if x[0] in validTable]

        answerList, _ = dt.transform(XList, Y, Q, reversedQS, queriedTableList)
        for aw in answerList:
            aw.X = Q_map.get(aw.X, aw.X)

        exampleAnswerList = scorer.exampleListToAnswer([*zip(XList, Y)], reversedQS)
        for ex in exampleAnswerList:
            ex.X = XList_map.get(ex.X, ex.X)
            ex.Y = Y_map.get(ex.Y, ex.Y)

        return exampleAnswerList, answerList, Q, reversedQS

    def reverseQuery(self, XList, Y, tidList):
        import json

        dbUtil = getDBUtil()

        qString = "SELECT id, content, confidence, openrank FROM tables_tokenized_full WHERE id IN {}"

        conn = dbUtil.getDBConn("postgres")
        cur = conn.cursor()
        if len(tidList) == 1:
            qString = qString.format("(" + str(tidList[0]) + ")")
        else:
            qString = qString.format(tuple(tidList))

        cur.execute(qString)

        tableJSON = {}
        round1Fail = 0
        round2Fail = 0
        for _id, content, confidence, openrank in cur:
            item_dict = {}

            item_dict["content"] = []
            try:
                tupleJSON = json.loads(content)
            except json.decoder.JSONDecodeError:
                print("round 1 fail" + str(_id))
                round1Fail += 1
                try:
                    tupleJSON = json.loads(dbUtil.__jsonClean(content))
                except json.decoder.JSONDecodeError:
                    print("round 2 fail" + str(_id))
                    round2Fail += 1
                    continue

            for tupleT in tupleJSON["tuples"]:
                cellList = tuple([cell.get("value", "") for cell in tupleT["cells"]])
                item_dict["content"].append(cellList)

            item_dict["confidence"] = confidence
            item_dict["openrank"] = max(openrank / 100.0, 0.0)
            item_dict["colid"] = [*range(len(cellList))]

            tableJSON[_id] = item_dict

        cur.close()
        conn.close()

        return tableJSON
