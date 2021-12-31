import argparse
from dxf.em import expectation_maximization

from wrapping.models.basic.evaluate import BasicEvaluator
from wrapping.models.basic.induce import BasicInduction
from wrapping.models.basic.reduce import BasicReducer
from wrapping.models.nielandt.induce import NielandtInduction
from wrapping.models.nielandt.reduce import NielandtReducer
from wrapping.tree.filter import TauMatchFilter
from wrapping.utils import load_and_prepare_examples
from wrapping.wrapper import wrap


def main():
    parser = argparse.ArgumentParser(description="")
    args = parser.parse_args()

    resource_filter = TauMatchFilter(2)
    evaluator = BasicEvaluator()
    reducer = NielandtReducer()
    induction = NielandtInduction()

    # file = (
    #     "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/test2.json"
    # )
    file = "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/n_14_k_3_5.json"
    example_split = 0.2

    examples, queries, queries_gt = load_and_prepare_examples(file, example_split)
    result = dict(expectation_maximization(set(examples), set(queries)))
    # print(
    #     wrap(
    #         examples,
    #         queries,
    #         resource_filter=resource_filter,
    #         evaluator=evaluator,
    #         reducer=reducer,
    #         induction=induction,
    #     )
    # )

    # print()
    # print("Examples: ", examples)
    # print("Queries: ", queries)
    # print("Queries (gt): ", dict(queries_gt))
    count = 0
    count_in = 0
    for key, target in queries_gt:
        print(f"{key}: {target} | {result[key]}")
        count += target==result[key]
        count_in += target in result[key]
    print(count/len(queries_gt))
    print(count_in/len(queries_gt))
        
if __name__ == "__main__":
    main()
