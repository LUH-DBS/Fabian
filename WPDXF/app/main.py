import argparse
import json
import random

from wrapping.wrapper import wrap

random.seed(0)


def load_and_prepare_examples(file, example_split=0.8):
    json_ex = json.load(open(file))
    if "queries" in json_ex:
        examples = json_ex["examples"]
        queries = json_ex["queries"]

    else:
        examples = random.sample(
            json_ex["examples"], int(len(json_ex["examples"]) * example_split)
        )
        queries = [ex for ex in json_ex["examples"] if ex not in examples]

    examples = [(ex["input"], ex["output"]) for ex in examples]
    queries_gt = [(q["input"], q["output"]) for q in queries]
    queries = [(q["input"], None) for q in queries]

    return examples, queries, queries_gt


def main():
    parser = argparse.ArgumentParser(description="")
    args = parser.parse_args()

    file = "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/test.json"
    # file = "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/res/examples/n_14_k_3_5.json"
    example_split = 0.5

    examples, queries, queries_gt = load_and_prepare_examples(file, example_split)
    wrap(examples, queries)

    print()
    print("Examples: ", examples)
    print("Queries: ", queries)
    print("Queries (gt): ", dict(queries_gt))


if __name__ == "__main__":
    main()
