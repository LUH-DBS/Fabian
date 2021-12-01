import json
import random

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
