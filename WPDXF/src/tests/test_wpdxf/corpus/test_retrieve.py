from os.path import join

import pytest
from wpdxf.utils.settings import Settings
from wpdxf.utils.stats import Statistics
from test_wpdxf.test_utils import clear_path, createArcWarcRecord, createWARC, generate_scenario
from wpdxf.utils.utils import decompress_file, read_file, read_json, write_file

from wpdxf.corpus.retrieval.wet.consume import wet_filter, yield_records
from wpdxf.corpus.retrieval.wet.retrieve import main_routine, sample_tasks


def test_wet_filter():
    wet_args = generate_scenario({})
    input = createArcWarcRecord(**wet_args)
    target = True

    output = wet_filter(input)
    assert output == target

    wet_args = generate_scenario({"record_type": "request"})
    input = createArcWarcRecord(**wet_args)
    target = False

    output = wet_filter(input)
    assert output == target

    wet_args = generate_scenario({"WARC-Identified-Content-Language": "eng, ger"})
    input = createArcWarcRecord(**wet_args)
    target = False

    output = wet_filter(input)
    assert output == target

    wet_args = generate_scenario({})
    del wet_args["warc_headers_dict"]["WARC-Identified-Content-Language"]
    input = createArcWarcRecord(**wet_args)
    target = False

    output = wet_filter(input)
    assert output == target

    wet_args = generate_scenario({"WARC-Identified-Content-Language": "ger, eng"})
    input = createArcWarcRecord(**wet_args)
    target = False

    output = wet_filter(input)
    assert output == target


def test_yield_records():
    filename = "four_records.wet.gz"
    filepath = join(Settings().WET_FILES, filename)
    wets = generate_scenario(
        [
            {},
            {"WARC-Identified-Content-Language": "ger, eng"},
            {"WARC-Identified-Content-Language": "ger"},
            {},
        ]
    )

    createWARC(filepath, wets)

    stat = Statistics.reset(filename)

    input = yield_records(filepath)
    target_sum = 2
    target_lang = 2

    output_sum = sum([1 for _ in input])
    assert output_sum == target_sum
    assert stat.rec_retrieval["accepted_total"] == target_sum
    assert stat.rec_retrieval["dropped_lang"] == target_lang


def test_main_routine():
    base_path = Settings().BASE_PATH
    clear_path(base_path)
    wets = generate_scenario(
        [
            {"payload": b"Some sample text.\nLet me see it in the term store."},
            {"WARC-Identified-Content-Language": "ger, eng"},
            {"WARC-Identified-Content-Language": "ger"},
            {"WARC-Identified-Content-Language": "eng"},
        ]
    )

    filename = "server/wet/main_routine.wet.gz"
    createWARC(
        base_path + filename, wets,
    )

    # Input
    write_file(Settings().WET_PATHS, filename)

    # Target
    target_sum = 2
    target_lang = 2
    target_error = []
    target_url_len = len("http://example.com")

    # Output
    main_routine(
        mp_method="fork"
    )  # Use fork to keep the same settings for all subprocesses
    stats = read_json(join(Settings().STATISTICS_PATH, "main_routine.wet.gz.json"))

    assert target_sum == stats["accepted_total"]
    assert target_lang == stats["dropped_lang"]
    assert target_error == stats["dropped_error"]
    assert target_url_len == stats["max_url_len"]
    with pytest.raises(FileNotFoundError):
        read_file(Settings().WET_FILES + filename)

    target_terms = [
        ["id0", "0", "sample"],
        ["id0", "1", "text"],
        ["id0", "2", "let"],
        ["id0", "3", "see"],
        ["id0", "4", "term"],
        ["id0", "5", "store"],
        ["id3", "0", "test"],
    ]
    output = list(
        map(
            lambda x: x.split(" "),
            decompress_file(Settings().TERM_STORE + "main_routine.wet.gz").split("\n")[
                :-1  # Drop last (empty) line
            ],
        )
    )
    assert target_terms == output

    target_mapping = [["id0", "http://example.com"], ["id3", "http://example.com"]]

    output = list(
        map(
            lambda x: x.split(" "),
            decompress_file(Settings().MAP_STORE + "main_routine.wet.gz").split("\n")[
                :-1  # Drop last (empty) line
            ],
        )
    )
    assert target_mapping == output


def test_sample_tasks():
    base_path = Settings().BASE_PATH
    clear_path(base_path)

    # Input
    path_num = 4
    wet_paths = sorted([f"patha/wet_path_{i}.test" for i in range(path_num)])
    write_file(Settings().WET_PATHS, "\n".join(wet_paths))

    # Unconstrained sampling
    target = wet_paths  # already sorted
    output = sorted(sample_tasks())
    assert output == target

    # Limited sampling
    target = 2
    output = len(sample_tasks(limit=2))
    assert output == target

    # Given files sampling
    target = set([wet_paths[0]])
    output = sample_tasks(exclude=set(map(lambda x: "pathb/" + x, wet_paths[1:])))
    assert output == target