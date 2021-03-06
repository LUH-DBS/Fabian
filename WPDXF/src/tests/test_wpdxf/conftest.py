import logging
import os

import pytest
from wpdxf.utils.settings import Settings

TEST_SETTINGS = (
    "/home/fabian/Documents/Uni/Masterarbeit/Fabian/WPDXF/src/test_settings.json"
)


@pytest.fixture(scope="session", autouse=True)
def setup():
    logging.basicConfig(filename="test.log", level=logging.INFO)
    s = Settings.change_settings(TEST_SETTINGS)
    os.makedirs(s.BASE_PATH, exist_ok=True)


@pytest.hookimpl()
def pytest_sessionfinish(session, exitstatus):
    if exitstatus == 0:
        # clear_path(settings.get("BASE_PATH"))
        ...
