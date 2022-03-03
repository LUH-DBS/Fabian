import gzip
import json
import os
from io import BytesIO
from typing import Union


def read_file(filepath: str, asStr: bool = True):
    with open(filepath, "r" + (not asStr) * "b") as f:
        content = f.read()
    return content


def compress_file(filepath: str, content: Union[str, bytes, BytesIO]):
    make_dirs(filepath)
    if isinstance(content, str):
        content = content.encode("utf-8")
    elif isinstance(content, BytesIO):
        content = content.getvalue()
    with gzip.open(filepath, "wb") as f:
        f.write(content)


def decompress_file(filepath: str, asStr: bool = True):
    if not os.path.exists(filepath):
        return ""
    with gzip.open(filepath) as f:
        content = f.read()

    if asStr:
        return content.decode("utf-8")
    else:
        return content


def write_file(filepath: str, content: Union[str, bytes]):
    with open_write(filepath, isinstance(content, bytes)) as f:
        f.write(content)


def open_write(filepath: str, bytes: bool = False):
    make_dirs(filepath)
    return open(filepath, "w" + bytes * "b")


def rm_file(filepath: str):
    if os.path.exists(filepath) and os.path.isfile(filepath):
        os.remove(filepath)


def make_dirs(filepath: str):
    path = os.path.dirname(filepath)
    if not os.path.exists(path):
        os.makedirs(path)


def read_json(filepath: str):
    if not os.path.exists(filepath):
        return {}
    with open(filepath) as f:
        j = json.load(f)
    return j


def write_json(filepath: str, content):
    make_dirs(filepath)
    with open_write(filepath) as f:
        json.dump(content, f)
