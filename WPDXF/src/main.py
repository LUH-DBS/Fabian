import argparse
import logging
from datetime import datetime
from enum import Enum
from os.path import abspath, basename, isfile, join, splitext
from typing import List

from pandas import DataFrame, read_csv

from dataXFormer.webtableindexer.Tokenizer import Tokenizer
from dataXFormer.webtables.TableScore import TableScorer
from wpdxf.tableretieval import WebPageRetrieval, WebTableRetrieval
from wpdxf.utils.report import ReportWriter

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

    return args.mode, [*zip(*split[::2])], [*zip(*split[1:2])], [*zip(*split[1::2])]


def main(mode, examples, queries, groundtruth):


    rw = ReportWriter()
    scorer = TableScorer()

    if mode is ModeArgs.WEBPAGE:
        with rw.start_timer("Answer Retrieval"):
            args = WebPageRetrieval().run(examples, queries)
    elif mode is ModeArgs.WEBTABLE:
        with rw.start_timer("Answer Retrieval"):
            args = WebTableRetrieval().run(examples, queries)
    else:
        return

    with rw.start_timer("Expectation Maximization"):
        answerList = scorer.expectionMaximization(*args)

    rw.write_answer(answerList, groundtruth, examples)


if __name__ == "__main__":
    args = parse_args()
    try:
        main(*args)
    except Exception as e:
        logging.exception("")
