from itertools import count
from typing import Dict, List, Set, Tuple

from wpdxf.utils.report import ReportWriter
from wpdxf.wrapping.objects.pairs import Example, Pair, Query
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
    for _resource in resources:
        resource = Resource(*_resource)

        with rw.start_timer(f"Eval0: {resource}"):
            evaluator.evaluate_initial(resource, examples, queries)
        rw.append_resource_info(f"Initial Evaluation: {resource}", resource.info())

        if not tau_filter(resource):
            continue

        with rw.start_timer(f"Red0: {resource}"):
            reducer.reduce_ambiguity(resource)
        rw.append_resource_info(f"Reduce Ambiguity: {resource}", resource.info())

        if not tau_filter(resource):
            continue

        cnt = count()
        while True:
            # Wrapper Induction
            iteration = next(cnt)
            with rw.start_timer(f"Induction ({iteration}) {resource}"):
                induction.induce(resource, examples)
            rw.append_resource_info(
                f"Induction ({iteration}): {resource}", resource.info()
            )
            # Wrapper evaluation
            with rw.start_timer(f"Eval ({iteration}) {resource}"):
                evaluator.evaluate(resource)

            table = create_table(resource, examples, queries)
            rw.append_query_evaluation(f"{iteration} - {resource}", table)

            table = reduce_table(table)
            if len([*filter(lambda x: x[1] is not None, table)]) >= tau:
                skip_resource = False
                break

            with rw.start_timer(f"Red ({iteration}) {resource}"):
                reducer.reduce(resource)
            rw.append_resource_info(f"Red ({iteration}) {resource}", resource.info())

            if not tau_filter(resource):
                skip_resource = True
                break

        if skip_resource:
            continue
        tables[resource] = table

    rw.end_timer()
    return tables


def create_table(
    resource: Resource, examples: List[Example], queries: List[Query]
) -> Dict[str, Set[str]]:
    res = {}

    def _collect(item_dict: dict, items:list):
        for pair in items:
            if not pair in item_dict:
                res[pair.inp] = set()
            else:
                res[pair.inp] = {
                    "".join(out.itertext()) for _, out, _ in item_dict[pair]
                }

    _collect(resource.examples(), examples)
    _collect(resource.queries(), queries)

    return res


def reduce_table(table: Dict[str, Set[str]]) -> List[Tuple[str, str]]:
    res = []
    for inp, outputs in table.items():
        if len(outputs) == 1:
            res.append((inp, outputs.pop()))
        elif len(outputs) > 1:
            for item in outputs:
                if all(item in _item for _item in outputs):
                    res.append((inp, outputs.pop()))
                    break
    return res
