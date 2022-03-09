import argparse
import logging
import os
from datetime import datetime
from enum import Enum
from os.path import abspath, basename, exists, isfile, join, splitext
from typing import List

from pandas import DataFrame, read_csv

from eval.em import TableScorer
from eval.sources import WebPageSource, WebTableSource
from wpdxf.utils.report import ReportWriter, Singleton

BENCHMARKS = "../data/benchmarks/"


class ModeArgs(str, Enum):
    WEBPAGE = "WP"
    WEBTABLE = "WT"
    FLASHEXTRACT = "FE"


def select_cols(idx_or_header, data):
    if isinstance(idx_or_header, int):
        return data.iloc[:, idx_or_header]
    elif isinstance(idx_or_header, str):
        return data[:, idx_or_header]
    else:
        raise ValueError(
            "All values of input and output must be of the same type (int or str)."
        )


def split_benchmark(
    *,
    benchmark: DataFrame,
    input: List[int or str],
    output: List[int or str],
    num_examples: int,
    # num_queries: int,
    seed: int,
    **kwargs,
):
    if num_examples > len(benchmark):
        raise ValueError("Benchmark contains too few values for evaluation.")

    data = benchmark.sample(frac=1, random_state=seed)
    data_inp = select_cols(input, data)
    data_out = select_cols(output, data)

    data_inp = data_inp.values.tolist()
    data_out = data_out.values.tolist()

    ex_X, q_X = data_inp[:num_examples], data_inp[num_examples:]
    ex_Y, q_Y = data_out[:num_examples], data_out[num_examples:]

    return ex_X, q_X, ex_Y, q_Y


def parse_benchmarks(path) -> List[str]:
    def parse_file_or_dir(p):
        if isfile(p):
            return [p]
        else:
            root, _, files = next(os.walk(p))
            files = list(
                map(
                    lambda f: join(root, f),
                    filter(lambda f: splitext(f)[1] == ".csv", files),
                )
            )
            return files

    # Search for valid path
    if exists(path):
        return parse_file_or_dir(path)
    elif exists(join(BENCHMARKS, path)):
        return parse_file_or_dir(join(BENCHMARKS, path))
    else:
        raise FileNotFoundError


def parse_args():
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
        type=str,
        required=True,
        help="File (csv) used for evaluation",
    )
    parser.add_argument(
        "--input", default=0, help="Index (int) or header (str) considered as input.",
    )
    parser.add_argument(
        "--output",
        default=-1,
        help="Indices (int) or headers (str) considered as output.",
    )
    parser.add_argument("--seed", default=0, type=int, help="Random seed")
    parser.add_argument("--num_examples", default=5, type=int)
    # parser.add_argument("--num_queries", default=5, type=int)
    parser.add_argument("--tau", default=2, type=int)
    parser.add_argument("--enrich_predicates", action="store_true")
    parser.add_argument("-tm", "--token_match", choices=["eq", "cn"], default="cn")
    parser.add_argument("-tf", "--max_rel_tf", default=0.01, type=float)

    args = parser.parse_args()

    # Check if benchmark is file or folder
    filenames = parse_benchmarks(args.benchmark)

    return filenames, args


def run_single_experiment(filename, args):

    benchmark = read_csv(filename, encoding="utf-8", encoding_errors="strict").astype(
        str
    )
    split = split_benchmark(
        benchmark=benchmark,
        input=args.input,
        output=args.output,
        num_examples=args.num_examples,
        seed=args.seed,
    )
    examples = [*zip(*split[::2])]
    queries = {*split[1]}
    groundtruth = [*zip(*split[1::2])]

    rw.write_metafile(
        filename=filename,
        date=datetime.now().isoformat(timespec="seconds"),
        examples=examples,
        queries=queries,
        groundtruth=groundtruth,
        **vars(args),
    )

    if args.mode is ModeArgs.WEBPAGE:
        source = WebPageSource(
            args.tau, args.enrich_predicates, args.token_match, args.max_rel_tf
        )
    elif args.mode is ModeArgs.WEBTABLE:
        source = WebTableSource(args.tau)
    elif args.mode is ModeArgs.FLASHEXTRACT:
        source = ...
    else:
        return

    scorer = TableScorer(source)
    with rw.start_timer("Expectation Maximization"):
        # print(examples, queries, sep="\n")
        examples, queries, groundtruth = source.prepare_input(
            examples, queries, groundtruth
        )
        answers = scorer.expectation_maximization(examples, queries)

    examples, answers, groundtruth = source.prepare_output(
        examples, answers, groundtruth
    )
    rw.write_answer(answers, groundtruth, examples)


if __name__ == "__main__":
    filenames, args = parse_args()
    for filename in filenames:
        filename_short = splitext(basename(filename))[0]
        rw = ReportWriter(f"{args.mode}-{filename_short}")
        try:
            run_single_experiment(filename, args)
        except Exception:
            logging.exception(f"Exception with {filename}")
        Singleton._instances = {}
