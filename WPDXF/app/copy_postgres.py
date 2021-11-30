import argparse
import logging
from db.PostgresDBSession import PostgresDBSession

def main():
    def check_gt_0(val):
        val = int(val)
        if val > 0:
            return val
        raise argparse.ArgumentTypeError()

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--amount", type=check_gt_0, required=True)

    logging.basicConfig(filename='copy.log', level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    args = parser.parse_args()
    conn = PostgresDBSession()
    conn.copy_from_sample(args.amount)


if __name__ == "__main__":
    main()
