import argparse

# import logging

from corpus.retrieval.wet.retrieve import main_routine


def main():
    parser = argparse.ArgumentParser(description="Missing.")
    parser.add_argument(
        "--retrieve", action="store_true", help="Retrieve new web pages."
    )
    # parser.add_argument(
    #     "--type", choices=["gzip", "print"], help="DBSession Type", required=True
    # )
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

    if args.retrieve:
        main_routine(**vars(args))


if __name__ == "__main__":
    main()
