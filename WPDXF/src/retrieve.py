import argparse

from wpdxf.corpus.retrieval.wet.retrieve import main_routine


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "--limit", type=int, required=True, help="The total number of files retrieved."
    )
    parser.add_argument(
        "--mp_method",
        choices=["spawn", "fork", None],
        default="spawn",
        help="Specify if the retrieval should run in multiprocessing mode.",
    )

    args = parser.parse_args()
    main_routine(**vars(args))


if __name__ == "__main__":
    main()
