
from wrapping.objects.pairs import Example, Query
from wrapping.objects.resource import Resource
from wrapping.tree.uritree import group_uris


def wrap(
    examples, queries, resource_filter, evaluator, reducer, induction, candidates=None
):
    # queries_original = queries
    # examples = [Example(i, *vals) for i, vals in enumerate(examples)]
    # off = len(examples)
    # queries = [Query(i + off, *vals) for i, vals in enumerate(queries)]
    print("Retrieve web pages (candidates)...")
    candidates = candidates or get_uris_for(examples, queries)

    print(f"Retrieved candidates (total: {len(candidates)}):")
    print(
        "\n".join(
            [f"{uri}: {matches}" for uri, matches in list(candidates.items())[:20]]
        ),
        "\n",
    )

    resource_groups = group_uris(candidates, resource_filter)
    print(
        f"Retrieval results in {len(resource_groups)} groups: {[id for id, _ in resource_groups[:20]]}"
    )
    wrap_result = []
    done = False
    for i in range(evaluator.TOTAL_EVALS):
        if done:
            break
        for resource in resource_groups:
            resource = Resource(*resource)
            evaluator.eval_initial(resource, examples, queries, i)
            if not resource_filter.filter(
                resource.matched_examples(), resource.matched_queries()
            ):
                print("Resource dropped due to bad initialization")
                continue
            else:
                done = True

            has_output = False
            while not has_output:
                has_output = True
                reducer.reduce(resource)
                if not resource_filter.filter(
                    resource.matched_examples(), resource.matched_queries()
                ):
                    continue

                induction.induce(resource, examples)
                # evaluate is not necessary
                evaluator.evaluate(resource, examples)

                print(f"Resulting resource:")
                q_dict = evaluator.evaluate_query(resource, queries=queries)
                query_results = dict(queries_original)

                overfull_cnt = len(query_results)
                empty_cnt = len(query_results)
                for q, vals in q_dict.items():
                    if len(vals) >= 1:
                        empty_cnt -= 1
                    if len(vals) <= 1:
                        overfull_cnt -= 1
                    if len(vals) == 1:
                        query_results[q.inp] = vals[0]
                if overfull_cnt > 2:
                    print("OVERFULL")
                    has_output = False
                    continue
                if empty_cnt > 2:
                    print("EMPTY")
                    continue

                wrap_result.append(
                    {
                        "resourceID": resource.id,
                        "rel_xpath": resource.out_xpath.as_xpath(
                            abs_start_path="$input"
                        ),
                        "mapping": query_results,
                    }
                )
    return wrap_result
