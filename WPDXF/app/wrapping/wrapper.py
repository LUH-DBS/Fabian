from wrapping.induce.basic import BasicInduction2
from db.queryGenerator import get_uris_for

from wrapping.evaluate.basic import BasicEvaluator
from wrapping.objects.resource import Resource
from wrapping.reduce.basic import BasicReducer
from wrapping.tree.filter import TauMatchFilter
from wrapping.tree.uritree import group_uris


def wrap(
    examples, queries, resource_filter, evaluator, reducer, induction, candidates=None
):
    print("Retrieve web pages (candidates)...")
    candidates = candidates or get_uris_for(examples, queries, "postgres")

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
    for resource in resource_groups:
        resource = Resource(*resource)
        if not evaluator.eval_initial(resource, examples, queries):
            print("Resource dropped due to bad initialization")
            continue

        reducer.reduce(resource, examples)

        while True:
            old_xpath = resource.out_xpath
            new_xpath = induction.induce(resource, examples)
            if old_xpath == new_xpath:
                break
            evaluator.evaluate(resource, examples=examples)
            reducer.reduce(resource, examples)

        # print(f"Resulting resource:")
        q_dict = evaluator.evaluate_query(resource, queries=queries)
        query_results = dict(queries)
        query_results.update(
            {queries[key][0]: val[0] for key, val in q_dict.items() if len(val) == 1}
        )
        wrap_result.append(
            {
                "resourceID": resource.id,
                "rel_xpath": resource.out_xpath,
                "mapping": query_results,
            }
        )
        # print(resource.id, resource.out_xpath)
        # print(query_results)
        # print()
    return wrap_result


if __name__ == "__main__":
    r = Resource("test", ["www.example.com", "www.example2.com"])
    wp = r.webpages[0]
    wp._html = """
<div>
<true>
<inputA>Test</inputA>
<output>Output</output>
</true>
<false>
<input>Test</input>
</false>
</div>
"""
    wp = r.webpages[1]
    wp._html = """
<div>
<true>
<inputB>Input</inputB>
<inputA>Test</inputA>
<output>Output</output>
</true>
<false>
<false>
<inputC>Input</inputC>
</false>
<input>Test</input>
</false>
</div>
"""
    examples = [("Test", "Output"), ("Input", "Output")]
    queries = [("Test", None)]
    res_filter = TauMatchFilter(1)
    evaluator = BasicEvaluator(res_filter)
    reducer = BasicReducer()
    evaluator.eval_initial(r, examples, queries)
    reducer.reduce(r)
    for wp in r.webpages:
        print(wp.uri)
        print(wp.inp_matches)
        print(wp.out_matches)
