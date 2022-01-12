from wpdxf.utils.report import ReportWriter
from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.resourceCollector import ResourceCollector


def wrap(
    examples, queries, query_executor, resource_filter, evaluator, reducer, induction
):
    rw = ReportWriter()

    examples = [Example(i, *ex) for i, ex in enumerate(examples)]
    queries = [Query(i + len(examples), q) for i, q in enumerate(queries)]

    print("Collecting Resources")
    resources = ResourceCollector(query_executor, resource_filter).collect(
        examples, queries
    )
    print(f"Resulted in {len(resources)} resources")

    tables = {}
    done = False
    rw.start_timer("Full Evaluation")
    for i in range(evaluator.TOTAL_EVALS):
        for _resource in resources:
            resource = Resource(*_resource)

            with rw.start_timer("Eval0: " + resource.id):
                evaluator.eval_initial(resource, examples, queries, i)
                do_continue = not resource_filter.filter(
                    resource.examples(), resource.queries()
                )
            rw.append_resource_info(
                "Initial Evaluation: " + resource.id, resource.info()
            )
            if do_continue:
                continue

            with rw.start_timer("Red0: " + resource.id):
                reducer.reduce_ambiguity(resource)
                do_continue = not resource_filter.filter(
                    resource.examples(), resource.queries()
                )
            rw.append_resource_info("Reduce Ambiguity: " + resource.id, resource.info())
            if do_continue:
                continue

            iteration = 0
            while True:
                iteration += 1
                # Wrapper Induction
                with rw.start_timer(f"Induction ({iteration}) {resource.id}"):
                    induction.induce(resource, examples)
                rw.append_resource_info(
                    f"Induction ({iteration}): " + resource.id, resource.info()
                )

                # Wrapper evaluation
                with rw.start_timer(f"Eval ({iteration}) {resource.id}"):
                    table = evaluator.evaluate_query(resource, examples, queries)
                rw.append_query_evaluation(f"{iteration} - {resource.id}", table)

                any_result = any(len(val) == 1 for val in table.values())
                if any_result:
                    table = set(
                        [
                            (p.inp, (v[0] if len(v) == 1 else None))
                            for p, v in table.items()
                        ]
                    )
                    skip_resource = False
                    done = True
                    break
                else:
                    with rw.start_timer(f"Red ({iteration}) {resource.id}"):
                        reducer.reduce(resource)
                        do_continue = not resource_filter.filter(
                            resource.examples(), resource.queries()
                        )
                    rw.append_resource_info(
                        f"Red ({iteration}) {resource.id}", resource.info()
                    )
                    if do_continue:
                        skip_resource = True
                        break

            if skip_resource:
                continue
            tables[resource.id] = table
        if done:
            break

    rw.end_timer()
    return tables


def prepare_resource(
    resource, evaluator, reducer, resource_filter, examples, queries, eval_type
):
    evaluator.eval_initial(resource, examples, queries, eval_type)
    if not resource_filter.filter(resource.examples(), resource.queries()):
        return False
    reducer.reduce_ambiguity(resource)
    if not resource_filter.filter(resource.examples(), resource.queries()):
        return False
    return True
