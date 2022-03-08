from itertools import count
from typing import Dict, List, Set, Tuple

from lxml.etree import _ElementUnicodeResult
from wpdxf.corpus.parsers.textparser import TextParser
from wpdxf.utils.report import ReportWriter
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.resourceCollector import ResourceCollector


def wrap(examples, queries, query_executor, tau, evaluator, reducer, induction):
    rw = ReportWriter()

    def tau_filter(resource: Resource):
        return len(resource.examples()) >= tau

    examples = [*map(lambda x: Example(*x), examples)]
    queries = [*map(Query, queries)]

    print("Collecting Resources")
    resources = ResourceCollector(query_executor, tau).collect(examples, queries)
    print(f"Resulted in {len(resources)} resources")
    tables = {}
    rw.start_timer("Full Evaluation")
    for i, _resource in enumerate(resources):
        resource = Resource(*_resource)
        print(f"Process Resource {i+1}: {resource.identifier}")

        with rw.start_timer(f"Eval0: {resource.identifier}"):
            evaluator.evaluate_initial(resource, examples, queries)
        rw.append_resource_info(
            f"Initial Evaluation: {resource.identifier}", resource.info()
        )

        if not tau_filter(resource):
            continue

        with rw.start_timer(f"Red0: {resource.identifier}"):
            reducer.reduce_ambiguity(resource)
        rw.append_resource_info(
            f"Reduce Ambiguity: {resource.identifier}", resource.info()
        )

        if not tau_filter(resource):
            continue

        cnt = count()
        while True:
            # Wrapper Induction
            iteration = next(cnt)
            with rw.start_timer(f"Induction ({iteration}) {resource.identifier}"):
                induction.induce(resource, examples)
            rw.append_resource_info(
                f"Induction ({iteration}): {resource.identifier}", resource.info()
            )
            # Wrapper evaluation
            with rw.start_timer(f"Eval ({iteration}) {resource.identifier}"):
                eval_result = evaluator.evaluate(resource, examples, queries)

            table = create_table(eval_result, examples, queries)
            rw.append_query_evaluation(f"{iteration} - {resource.identifier}\n{resource._xpath}\n{resource._vars}", table)

            table = reduce_table(table)
            if len([*filter(lambda x: x[1] is not None, table)]) >= tau:
                skip_resource = False
                break

            with rw.start_timer(f"Red ({iteration}) {resource.identifier}"):
                reducer.reduce(resource)
            rw.append_resource_info(
                f"Red ({iteration}) {resource.identifier}", resource.info()
            )

            if not tau_filter(resource):
                skip_resource = True
                break

        if skip_resource:
            continue

        tables[resource.identifier] = table

    rw.end_timer()
    return tables


def create_table(
    eval_result: dict, examples: List[Example], queries: List[Query]
) -> Dict[str, Set[str]]:
    res = {}
    tp = TextParser()

    for pair, items in eval_result.items():
        vals = set()
        for _, out in items:
            if isinstance(out, _ElementUnicodeResult):
                string = str(out)
            else:
                string = "".join(out.itertext())
            tokens = tp.tokenize_str(string, ignore_stopwords=False)
            if not tokens:
                continue
            tokens, _ = zip(*tokens)
            vals.add(" ".join(tokens))
        res[pair.inp] = vals

    return res


def reduce_table(table: Dict[str, Set[str]]) -> List[Tuple[str, str]]:
    res = []
    for inp, outputs in table.items():
        if len(outputs) == 1:
            res.append((inp, outputs.pop()))
        elif len(outputs) > 1:
            for item in outputs:
                if all(item in _item for _item in outputs):
                    res.append(inp, item)
                    break
            else:
                continue
        else:
            continue
    return res
