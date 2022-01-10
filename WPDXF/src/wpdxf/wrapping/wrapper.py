from wpdxf.wrapping.objects.pairs import Example, Query
from wpdxf.wrapping.objects.resource import Resource
from wpdxf.wrapping.objects.resourceCollector import ResourceCollector


def wrap(
    examples, queries, query_executor, resource_filter, evaluator, reducer, induction
):
    examples = [Example(i, *ex) for i, ex in enumerate(examples)]
    queries = [Query(i + len(examples), q) for i, q in enumerate(queries)]
    pairs = examples + queries

    print("Collecting Resources")
    resources = ResourceCollector(query_executor, resource_filter).collect(
        examples, queries
    )
    print(f"Resulted in {len(resources)} resources")

    tables = {}
    done = False
    for i in range(evaluator.TOTAL_EVALS):
        for _resource in resources:
            resource = Resource(*_resource)

            if not prepare_resource(
                resource,
                evaluator,
                reducer,
                resource_filter,
                examples,
                queries,
                eval_type=i,
            ):
                continue

            while True:
                induction.induce(resource, examples)
                # print(resource.out_xpath.as_xpath(abs_start_path="$input"))

                table = evaluator.evaluate_query(resource, examples, queries)
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
                    reducer.reduce(resource)
                    if resource_filter.filter(resource.examples(), set()):
                        continue
                    else:
                        skip_resource = True
                        break

            if skip_resource:
                continue
            tables[resource.id] = table
        if done:
            break
    return tables


def prepare_resource(
    resource, evaluator, reducer, resource_filter, examples, queries, eval_type
):
    evaluator.eval_initial(resource, examples, queries, eval_type)
    if not resource_filter.filter(resource.examples(), set()):
        return False
    reducer.reduce_ambiguity(resource)
    if not resource_filter.filter(resource.examples(), set()):
        return False
    return True


# def wrap(
#     examples, queries, resource_filter, evaluator, reducer, induction, candidates=None
# ):
#     # queries_original = queries
#     # examples = [Example(i, *vals) for i, vals in enumerate(examples)]
#     # off = len(examples)
#     # queries = [Query(i + off, *vals) for i, vals in enumerate(queries)]
#     print("Retrieve web pages (candidates)...")
#     candidates = candidates or get_uris_for(examples, queries)

#     print(f"Retrieved candidates (total: {len(candidates)}):")
#     print(
#         "\n".join(
#             [f"{uri}: {matches}" for uri, matches in list(candidates.items())[:20]]
#         ),
#         "\n",
#     )

#     resource_groups = group_uris(candidates, resource_filter)
#     print(
#         f"Retrieval results in {len(resource_groups)} groups: {[id for id, _ in resource_groups[:20]]}"
#     )
#     wrap_result = []
#     done = False
#     for i in range(evaluator.TOTAL_EVALS):
#         if done:
#             break
#         for resource in resource_groups:
#             resource = Resource(*resource)
#             evaluator.eval_initial(resource, examples, queries, i)
#             if not resource_filter.filter(
#                 resource.matched_examples(), resource.matched_queries()
#             ):
#                 print("Resource dropped due to bad initialization")
#                 continue
#             else:
#                 done = True

#             has_output = False
#             while not has_output:
#                 has_output = True
#                 reducer.reduce(resource)
#                 if not resource_filter.filter(
#                     resource.matched_examples(), resource.matched_queries()
#                 ):
#                     continue

#                 induction.induce(resource, examples)
#                 # evaluate is not necessary
#                 evaluator.evaluate(resource, examples)

#                 print(f"Resulting resource:")
#                 q_dict = evaluator.evaluate_query(resource, queries=queries)
#                 query_results = dict(queries_original)

#                 overfull_cnt = len(query_results)
#                 empty_cnt = len(query_results)
#                 for q, vals in q_dict.items():
#                     if len(vals) >= 1:
#                         empty_cnt -= 1
#                     if len(vals) <= 1:
#                         overfull_cnt -= 1
#                     if len(vals) == 1:
#                         query_results[q.inp] = vals[0]
#                 if overfull_cnt > 2:
#                     print("OVERFULL")
#                     has_output = False
#                     continue
#                 if empty_cnt > 2:
#                     print("EMPTY")
#                     continue

#                 wrap_result.append(
#                     {
#                         "resourceID": resource.id,
#                         "rel_xpath": resource.out_xpath.as_xpath(
#                             abs_start_path="$input"
#                         ),
#                         "mapping": query_results,
#                     }
#                 )
#     return wrap_result
