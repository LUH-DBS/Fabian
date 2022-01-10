from io import BytesIO

from utils.stats import Statistics
from utils.settings import Settings

from corpus.parsers.textparser import TextParser


def test_clean_and_token():
    # Ignore tailing punctuation
    input = BytesIO(b"Input.")
    target = [("input", 0)]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

    # Handling whitespaces
    input = BytesIO(b"InputA  InputB.\tInputC\nInputD\n")
    target = [("inputa", 0), ("inputb", 1), ("inputc", 2), ("inputd", 3)]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

    # Keep structural punctuation (surrounded by non-whitespace characters)
    input = BytesIO(b"- Input: 2021-10-29, https://www.example.org/ Input/Output")
    target = [
        ("input", 0),
        ("2021", 1),
        ("10", 2),
        ("29", 3),
        ("https", 4),
        ("www", 5),
        ("example", 6),
        ("org", 7),
        ("input", 8),
        ("output", 9),
    ]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

    input = BytesIO(
        b"2,33, 0.4\n 9:00, 9 p.m.; 9 am"
    )  # 'am' would be removed as it is a stopword
    target = [
        ("2,33", 0),
        ("0.4", 1),
        ("9", 2),
        ("00", 3),
        ("9", 4),
        ("p", 5),
        ("m", 6),
        ("9", 7),
        ("am", 8),
    ]

    tp = TextParser()
    assert list(tp.tokenize(input, ignore_stopwords=False)) == target

    input = BytesIO("Test (alias Tset) [optional]{curly brackets} <end>".encode("utf-8"))
    target = [
        ("test", 0),
        ("alias", 1),
        ("tset", 2),
        ("optional", 3),
        ("curly", 4),
        ("brackets", 5),
        ("end", 6),
    ]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

    # Remove stopwords
    Statistics.reset("")
    input = BytesIO(
        b"This is a test. It contains some of the most common words, which are also included in the stopwords."
    )
    target = [
        ("test", 0),
        ("contains", 1),
        ("common", 2),
        ("words", 3),
        ("also", 4),
        ("included", 5),
        ("stopwords", 6),
    ]
    target_efficiency = 7 / 19

    tp = TextParser()
    assert list(tp.tokenize(input)) == target
    assert Statistics().rec_retrieval["stopword_efficiency"] == target_efficiency

    # Exceed max_token_len
    max_token_len = Settings().MAX_TOKEN_LEN
    input = BytesIO(b"A" * 2 * max_token_len)
    target = [
        ("a" * max_token_len, 0),
        ("a" * max_token_len, 1),
    ]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

    input = BytesIO(b"A" * (max_token_len + 1))
    target = [
        ("a" * max_token_len, 0),
        ("a", 1),
    ]

    tp = TextParser()
    assert list(tp.tokenize(input)) == target

