from os.path import join

from wpdxf.utils.utils import read_json

DEFAULT_SETTINGS = (
    "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/src/settings.json"
)


class Settings:
    __valid_paths__ = set(
        [
            "STATISTICS_PATH",
            "WET_PATHS",
            "WET_FILES",
            "WARC_FILES",
            "STOP_WORDS",
            "TERM_STORE",
            "MAP_STORE",
            "URL_CACHE",
            "ERROR_PATH",
            "LOG_PATH",
        ]
    )
    __valid_vals__ = set(
        [
            "BASE_PATH",
            "CC_DOMAIN",
            "VERTICA_CONFIG",
            "POSTGRES_CONFIG",
            "NUM_PRODUCER",
            "NUM_CONSUMER",
            "UPDATE_STATS_EACH",
            "MAX_TOKEN_LEN",
            "MAX_CORPUS_FREQ",
        ]
    )

    _settings = None
    used_settings = DEFAULT_SETTINGS
    settings_dir = None

    def __new__(cls):
        if cls._settings is None:
            cls._settings = super(Settings, cls).__new__(cls)
            cls.settings_dir = read_json(cls.used_settings)
        return cls._settings

    @classmethod
    def change_settings(cls, new_settings):
        cls.used_settings = new_settings
        cls._settings = None
        return Settings()

    def __getattr__(self, name: str):
        if name in self.__valid_paths__:
            return join(
                self.settings_dir["BASE_PATH"], self.settings_dir["paths"][name]
            )
        if name in self.__valid_vals__:
            return self.settings_dir[name]
        raise AttributeError
