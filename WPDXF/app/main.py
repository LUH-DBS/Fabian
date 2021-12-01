import argparse

from wrapping.evaluate.basic import BasicEvaluator
from wrapping.induce.basic import BasicInduction
from wrapping.reduce.basic import BasicReducer
from wrapping.tree.filter import TauMatchFilter
from wrapping.utils import load_and_prepare_examples
from wrapping.wrapper import wrap


def main():
    parser = argparse.ArgumentParser(description="")
    args = parser.parse_args()

    resource_filter = TauMatchFilter(2)
    evaluator = BasicEvaluator(resource_filter)
    reducer = BasicReducer()
    induction = BasicInduction()

    # file = (
    #     "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/test2.json"
    # )
    file = "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/n_14_k_3_5.json"
    example_split = 0.5

    examples, queries, queries_gt = load_and_prepare_examples(file, example_split)
    wrap(
        examples,
        queries,
        resource_filter=resource_filter,
        evaluator=evaluator,
        reducer=reducer,
        induction=induction,
    )

    print()
    print("Examples: ", examples)
    print("Queries: ", queries)
    print("Queries (gt): ", dict(queries_gt))


if __name__ == "__main__":
    main()
