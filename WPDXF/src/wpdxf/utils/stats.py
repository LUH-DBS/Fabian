from os.path import join

from wpdxf.utils.settings import Settings
from wpdxf.utils.utils import read_json, write_json


class Statistics:
    _statistics = None
    # accept_total + dropped_lang = sum of all responses (websites) containing text
    # accepted_total - dropped_error = locally stored websites

    def __new__(cls):
        if cls._statistics is None:
            cls._statistics = super(Statistics, cls).__new__(cls)
            cls.rec_retrieval = {
                "accepted_total": 0,
                "dropped_lang": 0,
                "dropped_error": [],
                "max_url_len": 0,
                "stopword_efficiency": 0,  # average of reduced tokens/total tokens over accepted records (calculated per sentence)
                "stopword_count": 0,
            }
        return cls._statistics

    @classmethod
    def reset(cls, archive_name: str):
        cls._statistics = None
        s = Statistics()
        s.filepath = join(Settings().STATISTICS_PATH, archive_name + ".json")
        return s

    def __str__(self) -> str:
        return str(self.rec_retrieval)

    def inc_accepted(self):
        self.rec_retrieval["accepted_total"] += 1

    def inc_drop_lang(self):
        self.rec_retrieval["dropped_lang"] += 1

    def add_drop_error(self, item):
        self.rec_retrieval["dropped_error"].append(item)

    def max_url_len(self, length):
        self.rec_retrieval["max_url_len"] = max(
            self.rec_retrieval["max_url_len"], length
        )

    def update_stopword_eff(self, full_size, red_size):
        if full_size == 0:
            return

        old_mean = self.rec_retrieval["stopword_efficiency"]
        old_cnt = self.rec_retrieval["stopword_count"]
        self.rec_retrieval["stopword_efficiency"] = (
            old_cnt * old_mean + (red_size / full_size)
        ) / (old_cnt + 1)
        self.rec_retrieval["stopword_count"] += 1

    def update_record_retrieval(self):
        stats = read_json(self.filepath)
        stats.update(**self.rec_retrieval)
        write_json(self.filepath, stats)
