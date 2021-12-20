from db.queryGenerator import get_uris_for

from wrapping.models.basic.evaluate import BasicEvaluator
from wrapping.models.nielandt.induce import NielandtInduction
from wrapping.models.nielandt.reduce import NielandtReducer
from wrapping.objects.pairs import Example, Query
from wrapping.objects.resource import Resource
from wrapping.tree.filter import TauMatchFilter
from wrapping.tree.uritree import group_uris
from wrapping.utils import load_and_prepare_examples


def wrap(
    examples, queries, resource_filter, evaluator, reducer, induction, candidates=None
):
    queries_original = queries
    examples = [Example(i, *vals) for i, vals in enumerate(examples)]
    off = len(examples)
    queries = [Query(i + off, *vals) for i, vals in enumerate(queries)]
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
                print(resource.matched_examples(), resource.matched_queries())
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
                print(q_dict)
                for q, vals in q_dict.items():
                    if len(vals) >= 1:
                        empty_cnt -= 1
                    if len(vals) <= 1:
                        overfull_cnt -= 1
                    if len(vals) == 1:
                        query_results[q.inp] = vals[0]
                print(resource.out_xpath.as_xpath(abs_start_path="$input"))
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


if __name__ == "__main__":
    r = Resource(
        "www.thetimes.co.uk",
        [
            "https://www.thetimes.co.uk/article/brace-yourselves-returns-on-property-could-fall-by-a-tenth-this-year-b6kml0vvngj",
            "https://www.thetimes.co.uk/article/cafe-society-in-edinburgh-is-promised-a-cannabis-alternative-6jkqrzjqnln",
            "https://www.thetimes.co.uk/article/dupont-swallows-new-ingredient-2mfvvsh3hdj",
            "https://www.thetimes.co.uk/article/gangs-know-they-can-hack-and-slash-and-get-away-with-it-in-london-war-zone-5hzf082td",
            "https://www.thetimes.co.uk/article/reader-rescue-989j73rwzlk",
            "https://www.thetimes.co.uk/article/bunker-error-costs-miguel-angel-jimenez-course-record-at-royal-porthcawl-bqfhq788g",
            "https://www.thetimes.co.uk/article/inner-vision-dl7bvxgmrmx",
            "https://www.thetimes.co.uk/article/james-milners-hamstring-injury-stirs-fury-over-dangerous-workload-8mwl5zr68",
            "https://www.thetimes.co.uk/article/legal-amp-general-sees-growing-appeal-of-family-homes-to-rent-lxjc5prb9",
            "https://www.thetimes.co.uk/article/rumours-of-talks-with-carlsberg-cheer-sandn-vnprwgs90vr",
            "https://www.thetimes.co.uk/article/witness-to-auschwitz-horror-dies-at-82-tnl6czvm2c6",
        ],
    )
    examples, queries, _ = load_and_prepare_examples(
        "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/n_14_k_3_5.json",
        0.5,
    )
    examples = [Example(i, *vals) for i, vals in enumerate(examples)]
    queries = [Query(i, *vals) for i, vals in enumerate(queries)]
    resource_filter = TauMatchFilter(2)
    evaluator = BasicEvaluator(resource_filter)
    induction = NielandtInduction()
    reducer = NielandtReducer()
    evaluator.eval_initial(r, examples, queries, 0)
    reducer.reduce(r)

    # for wp in r.webpages:
    #     print(wp.uri)
    #     print(wp.input_matches())
    #     print(wp.relative_xpaths())
    # print(r.relative_xpaths())

    induction.induce(r)
    print()
    print(r.out_xpath)
    print()
    evaluator.evaluate(r, examples)

    # for wp in r.webpages:
    #     print(wp.uri)
    #     print(wp.input_matches())
    #     print(wp.relative_xpaths())
    # print(r.relative_xpaths())
    # print()
    # print(r.relative_xpaths(select="false"))
