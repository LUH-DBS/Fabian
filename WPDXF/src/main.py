import argparse
from difflib import SequenceMatcher
from enum import Enum
from os.path import abspath, isfile, join
from typing import List

from pandas import DataFrame, read_csv

from dataXFormer.webtables.TableScore import TableScorer
from wpdxf.tableretieval import WebPageRetrieval, WebTableRetrieval
# WebPage DataXFormer
from wpdxf.wrapping.models.basic.evaluate import BasicEvaluator
from wpdxf.wrapping.models.nielandt.induce import NielandtInduction
from wpdxf.wrapping.models.nielandt.reduce import NielandtReducer
from wpdxf.wrapping.tree.filter import TauMatchFilter

BENCHMARKS = "../data/benchmarks/"


class ModeArgs(str, Enum):
    WEBPAGE = "WP"
    WEBTABLE = "WT"
    FLASHEXTRACT = "FE"


def split_benchmark(
    benchmark: DataFrame,
    input: List[int or str],
    output: List[int or str],
    num_examples: int,
    num_queries: int,
    seed: int,
    *args,
    **kwargs,
):
    if num_examples + num_queries > len(benchmark):
        raise ValueError("Benchmark contains too few values for evaluation.")

    data = benchmark.sample(num_examples + num_queries, random_state=seed)

    if all(isinstance(x, int) for x in input + output):
        data_inp = data.iloc[:, input]
        data_out = data.iloc[:, output]
    elif all(isinstance(x, str) for x in input + output):
        data_inp = data[:, input]
        data_out = data[:, output]
    else:
        raise ValueError(
            "All values of input and output must be of the same type (int or str)."
        )

    data_inp = data_inp.values.tolist()
    data_out = data_out.values.tolist()

    ex_X, q_X = data_inp[:num_examples], data_inp[num_examples:]
    ex_Y, q_Y = data_out[:num_examples], data_out[num_examples:]

    return ex_X, q_X, ex_Y, q_Y


def parse_args():
    def dataframe(file):
        # Search for valid path
        # Input is a valid path itself.
        if isfile(file):
            filepath = file
        # Input is a valid path relative to the default benchmark dir.
        elif isfile(join(BENCHMARKS, file)):
            filepath = join(BENCHMARKS, file)
        else:
            raise FileNotFoundError
        filepath = abspath(filepath)
        return read_csv(filepath, encoding="utf-8", encoding_errors="strict")

    parser = argparse.ArgumentParser(description="")
    # Evaluation mode
    choices = [m.value for m in ModeArgs]
    parser.add_argument(
        "-m",
        "--mode",
        choices=choices,
        default=choices[0],
        type=lambda x: ModeArgs(x),
        help="Approach used for evaluaiton",
    )
    parser.add_argument(
        "-b",
        "--benchmark",
        type=dataframe,
        required=True,
        help="File (csv) used for evaluation",
    )
    parser.add_argument(
        "--input",
        default=[0],
        help="List of indices (int) or headers (str) considered as input.",
    )
    parser.add_argument(
        "--output",
        default=[-1],
        help="List of indices (int) or headers (str) considered as output.",
    )
    parser.add_argument("--seed", default=0, type=int, help="Random seed")
    parser.add_argument("--num_examples", default=2, type=int)
    parser.add_argument("--num_queries", default=8, type=int)

    args = parser.parse_args()
    split = split_benchmark(**vars(args))

    return args.mode, split[::2], split[1:2], split[1::2]


def main():
    mode, examples, queries, groundtruth = parse_args()
    groundtruth = [(x[0], y[0]) for x, y in zip(*(examples))] + [
        (x[0], y[0]) for x, y in zip(*(groundtruth))
    ]
    print(mode, examples, queries, groundtruth, sep="\n")
    scorer = TableScorer()

    if mode is ModeArgs.WEBPAGE:
        args = WebPageRetrieval(
            resource_filter=TauMatchFilter(2),
            evaluation=BasicEvaluator(),
            reduction=NielandtReducer(),
            induction=NielandtInduction(),
        ).run(examples, queries)
    elif mode is ModeArgs.WEBTABLE:
        args = WebTableRetrieval().run(examples, queries)
    else:
        return

    answerList = scorer.expectionMaximization(*args)

    total, correct = 0, 0
    overview = DataFrame(columns=["X", "Y", "Y (gt)", "Diff", "Score"])
    sm = SequenceMatcher()
    for answer in answerList:
        total += 1
        y_gt = [y for x, y in groundtruth if x == answer.X]
        if not y_gt:
            continue
        y_gt = y_gt[0]

        sm.set_seqs(answer.Y or "", y_gt or "")
        overview = overview.append(
            {
                "X": answer.X,
                "Y": answer.Y,
                "Y (gt)": y_gt,
                "Diff": sm.ratio(),
                "Score": float(answer.score),
            },
            ignore_index=True,
        )
        if answer.Y == y_gt:
            correct += 1
    print(overview.sort_values(["X", "Score"], ascending=[True, False]))
    print(correct / total)
    overview = overview.loc[overview.groupby("X")["Score"].idxmax()]
    correct = 0
    for idx, (x,  y, y_gt, diff, score) in overview.iterrows():
        correct += y == y_gt

    print(overview)
    print(correct / total)


if __name__ == "__main__":
    main()
