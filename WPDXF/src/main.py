import argparse
import logging
from datetime import datetime
from enum import Enum
from os.path import abspath, basename, isfile, join, splitext
from typing import List

from pandas import DataFrame, read_csv

from eval.em import TableScorer
from eval.sources import WebPageSource, WebTableSource
from wpdxf.utils.report import ReportWriter

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
    data_inp = select_cols(input, data)
    data_out = select_cols(output, data)

    data_inp = data_inp.values.tolist()
    data_out = data_out.values.tolist()

    ex_X, q_X = data_inp[:num_examples], data_inp[num_examples:]
    ex_Y, q_Y = data_out[:num_examples], data_out[num_examples:]

    return ex_X, q_X, ex_Y, q_Y


def parse_args():
    filename = []

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
        filename.append(filepath)
        return read_csv(filepath, encoding="utf-8", encoding_errors="strict").astype(
            str
        )

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
    parser.add_argument("--num_queries", default=5, type=int)
    parser.add_argument("--tau", default=2, type=int)

    args = parser.parse_args()
    args.filename = args.benchmark
    args.benchmark = dataframe(args.benchmark)

    filename_short = splitext(basename(args.filename))[0]
    rw = ReportWriter(f"{args.mode}-{filename_short}")

    rw.write_metafile(
        filename=filename[0],
        date=datetime.now().isoformat(timespec="seconds"),
        mode=args.mode,
        inputCols=args.input,
        outputCols=args.output,
        seed=args.seed,
        num_examples=args.num_examples,
        num_queries=args.num_queries,
    )

    split = split_benchmark(**vars(args))
    examples = [*zip(*split[::2])]
    queries = {*split[1]}
    groundtruth = [*zip(*split[1::2])]

    return args.mode, examples, queries, groundtruth, args.tau


def main(mode, examples, queries, groundtruth, tau):
    rw = ReportWriter()

    if mode is ModeArgs.WEBPAGE:
        source = WebPageSource(tau)
    elif mode is ModeArgs.WEBTABLE:
        source = WebTableSource(tau)
    elif mode is ModeArgs.FLASHEXTRACT:
        source = ...
    else:
        return

    scorer = TableScorer(source)
    with rw.start_timer("Expectation Maximization"):
        print(examples, queries, sep="\n")
        examples, queries, groundtruth = source.prepare_input(
            examples, queries, groundtruth
        )
        answers = scorer.expectation_maximization(examples, queries)

    examples, answers, groundtruth = source.prepare_output(
        examples, answers, groundtruth
    )
    rw.write_answer(answers, groundtruth, examples)


if __name__ == "__main__":
    try:
        args = parse_args()
        main(*args)
    except Exception as e:
        logging.exception("")
