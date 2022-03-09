import logging
from difflib import SequenceMatcher
from os import makedirs
from os.path import abspath, isdir, join
from time import time

from DataXFormer.webtableindexer.Tokenizer import Tokenizer
from pandas.core.frame import DataFrame

BASEDIR = "../data/reports"


def _csv_row(*args):
    return ",".join(f'"{arg}"' for arg in args) + "\n"


class Singleton(type):
    # TODO: Adapt the metaclass Singleton to other Singletons (Settings,...)
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def replace_filehandler(filename):
    log = logging.getLogger()
    for handler in log.handlers:
        log.removeHandler(handler)
    handler = logging.FileHandler(filename)
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    return log


class ReportWriter(metaclass=Singleton):
    _timer = []

    def __init__(self, dirname):
        self.rootdir = self.make_rootdir(dirname)
        self.logfile = join(self.rootdir, "logfile.log")
        self.logger = replace_filehandler(self.logfile)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.end_timer()

    def make_rootdir(self, dirname):
        basedir = abspath(BASEDIR)
        cnt = 0
        while isdir(join(basedir, dirname + str(cnt))):
            cnt += 1
        rootdir = join(basedir, dirname + str(cnt))
        makedirs(rootdir)
        return rootdir

    def write_metafile(self, **kwargs):
        with open(join(self.rootdir, "metafile.txt"), "w+") as f:
            for key, value in kwargs.items():
                f.write(f"{key}: {value}\n")

    def append_timing(self, key, start, end):
        with open(join(self.rootdir, "timing.csv"), "a+") as f:
            f.write(_csv_row(key, start, end, end - start))

    def start_timer(self, key):
        self._timer.append((key, time()))
        return self

    def end_timer(self):
        end = time()
        key, start = self._timer.pop()
        self.append_timing(key, start, end)

    def write_query_result(self, uris):
        uri_items = sorted(uris.items(), key=lambda x: x[0])
        with open(join(self.rootdir, "uris.csv"), "w+") as f:
            for key, (ex, q) in uri_items:
                f.write(_csv_row(key, ex, q))

    def write_uri_groups(self, groups):
        with open(join(self.rootdir, "groups.txt"), "w+") as f:
            f.write(f"{len(groups)} groups:\n")
            f.write("\n".join([str(group) for group in groups]))

    def write_answer(self, answer_list, groundtruth, examples):
        sm = SequenceMatcher()
        df = DataFrame(columns=["X", "Y", "Y (inp)", "Y (gt)", "Ratio", "Score"])

        for x, y_gt in examples:
            all_y = answer_list.get(x)
            df_dict = {"X": x, "Y (inp)": y_gt, "Y (gt)": y_gt}

            if all_y:
                for out, score in all_y.items():
                    sm.set_seqs(out, y_gt)
                    df_dict.update(**{"Y": out, "Ratio": sm.ratio(), "Score": score})
                    df = df.append(df_dict, ignore_index=True)
            else:
                df_dict.update(**{"Y": "", "Ratio": 0, "Score": -1.0})
                df = df.append(df_dict, ignore_index=True)

        for x, y_gt in groundtruth:
            all_y = answer_list.get(x)
            df_dict = {"X": x, "Y (inp)": "", "Y (gt)": y_gt}

            if all_y:
                for out, score in all_y.items():
                    sm.set_seqs(out, y_gt)
                    df_dict.update(**{"Y": out, "Ratio": sm.ratio(), "Score": score})
                    df = df.append(df_dict, ignore_index=True,)
            else:
                df_dict.update(**{"Y": "", "Ratio": 0, "Score": -1.0})
                df = df.append(df_dict, ignore_index=True)

        df = df.astype({"Score": "float"})
        df = df.sort_values(["X", "Score"], ascending=[True, False])
        df.to_csv(join(self.rootdir, "answerList.csv"), index=False)
        df = df.loc[df.groupby("X")["Score"].idxmax()]
        total = len(df)
        answered, correct = 0, 0
        for idx, (x, y, _, y_gt, *_) in df.iterrows():
            if y != "":
                answered += 1
                correct += y == y_gt

        precision = correct / answered if answered else 0
        recall = answered / total if total else 0
        print(f"Precision: {precision}, Recall: {recall}")
        self.logger.info(df)
        self.logger.info(f"Precision: {precision}, Recall: {recall}")

        df.to_csv(join(self.rootdir, "answer.csv"), index=False)

        self.append_kwargs_info("Result", precision=precision, recall=recall)

    def append_resource_info(self, key, info):
        with open(join(self.rootdir, "report.txt"), "a+") as f:
            f.write(f"RESOURCE INFO: {key}\n")
            f.write(info + "\n")

    def append_kwargs_info(self, key, **kwargs):
        with open(join(self.rootdir, "report.txt"), "a+") as f:
            f.write(f"KWARGS INFO: {key}\n")
            for key, value in kwargs.items():
                f.write(f"{key}: {value}\n")

    def append_query_evaluation(self, key, table):
        with open(join(self.rootdir, "tables.txt"), "a+") as f:
            f.write(key + "\n")
            for key, values in table.items():
                f.write(f"{key}: {values}\n")

    def append_em_scores(self, iteration, answer_scores, table_scores, delta):
        with open(join(self.rootdir, "em.txt"), "a+") as f:
            f.write(
                f"Iteration {iteration}\nDelta: {delta}\nAnswer Scores ({len(answer_scores)}):\n"
            )
            [f.write(str(item) + "\n") for item in answer_scores.items()]
            f.write(f"Table Scores ({len(table_scores)}):\n")
            [f.write(str(item) + "\n") for item in table_scores.items()]
