from db.queryGenerator import get_uris_for

from wrapping.evaluate.basic import BasicEvaluator
from wrapping.induction import induct
from wrapping.objects.resource import Resource
from wrapping.reduce.basic import BasicReducer
from wrapping.tree.filter import TauMatchFilter
from wrapping.tree.uritree import group_uris


def wrap(examples, queries, candidates=None):
    res_filter = TauMatchFilter(1)
    evaluator = BasicEvaluator(res_filter)
    reducer = BasicReducer()

    print("Retrieve web pages (candidates)...")
    candidates = candidates or get_uris_for(examples, queries, "postgres")

    print("Retrieved candidates:")
    print("\n".join([f"{uri}: {matches}" for uri, matches in candidates.items()]))

    resource_groups = group_uris(candidates, res_filter)
    print(
        f"Retrieval results in {len(resource_groups)} groups: {[id for id, _ in resource_groups[:20]]}"
    )
    for resource in resource_groups:
        resource = Resource(*resource)
        if not evaluator.eval_initial(resource, examples, queries):
            print("Resource dropped due to bad initialization")
            return

        reducer.reduce(resource, examples)

        while True:
            old_xpath = resource.out_xpath
            new_xpath = induct(resource, examples)
            if old_xpath == new_xpath:
                break
            evaluator.evaluate(resource, examples=examples)
            reducer.reduce(resource, examples)

        print(f"Resulting resource:")
        q_dict = evaluator.evaluate_query(resource, queries=queries)
        query_results = dict(queries)
        query_results.update(
            {queries[key][0]: val[0] for key, val in q_dict.items() if len(val) == 1}
        )
        print(resource.id, resource.out_xpath)
        print(query_results)
        print()
