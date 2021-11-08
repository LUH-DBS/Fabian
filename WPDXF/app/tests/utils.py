import os
from io import BytesIO
from typing import Union

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import BufferWARCWriter, WARCWriter

from utils import open_write

HTML_PAYLOAD = b"<html><body>This is a test.<body/><html/>"
TEXT_PAYLOAD = b"This is a test."

VALID_WARC_HEADERS = {
    "WARC-Identified-Payload-Type": "text/html",
    "WARC-Record-ID": "uniquewarcid",
}
VALID_WARC_ARGS = {
    "uri": "http://example.com",
    "record_type": "response",
    "warc_headers_dict": VALID_WARC_HEADERS,
    "payload": HTML_PAYLOAD,
    "headers_list": [],
}
VALID_WET_HEADERS = {
    "WARC-Identified-Content-Language": "eng",
    "WARC-Refers-To": "uniquewarcid",
}
VALID_WET_ARGS = {
    "uri": "http://example.com",
    "record_type": "conversion",
    "warc_headers_dict": VALID_WET_HEADERS,
    "payload": HTML_PAYLOAD,
    "headers_list": [],
}


def get_valid_warc(record_id=None):
    warc_dict = VALID_WARC_ARGS.copy()
    warc_dict["warc_headers_dict"] = VALID_WARC_HEADERS.copy()
    if record_id:
        warc_dict["warc_headers_dict"].update({"WARC-Record-ID": record_id})
    return warc_dict


def get_valid_wet(record_id=None):
    wet_dict = VALID_WET_ARGS.copy()
    wet_dict["warc_headers_dict"] = VALID_WET_HEADERS.copy()
    if record_id:
        wet_dict["warc_headers_dict"].update({"WARC-Refers-To": record_id})
    return wet_dict


def generate_scenario(configs):
    wets = []
    for id, conf in enumerate(configs):
        wet = get_valid_wet(f"id{id}")
        for key, value in conf.items():
            if key in wet:
                wet[key] = value
            elif key in wet["warc_headers_dict"]:
                wet["warc_headers_dict"][key] = value
        wets.append(wet)
    return wets


def createArcWarcRecord(writer=None, **kwargs):
    def parse_kwargs(kwargs):
        # HTTP HEADERS: Convert Headers list to StatusAndHeaders if given
        if "headers_list" in kwargs:
            kwargs["http_headers"] = StatusAndHeaders(
                "200 OK", kwargs["headers_list"], protocol="HTTP/1.0"
            )
            del kwargs["headers_list"]

        if "payload" in kwargs:
            if not isinstance(kwargs["payload"], BytesIO):
                kwargs["payload"] = BytesIO(kwargs["payload"])
        return kwargs

    kwargs = parse_kwargs(kwargs)
    if writer is None:
        writer = BufferWARCWriter(gzip=True)
        writer.warc_version = 'WARC/1.1'
    return writer.create_warc_record(**kwargs)


def createWARC(filepath, recargs: Union[dict, list]):

    if isinstance(recargs, dict):
        recargs = [recargs]

    with open_write(filepath, True) as fwarc:
        writer = WARCWriter(fwarc, gzip=True, warc_version = 'WARC/1.1')

        for kwargs in recargs:
            record = createArcWarcRecord(writer, **kwargs)
            writer.write_record(record)


def clear_path(path):
    for p in os.listdir(path):
        p = os.path.join(path, p)
        if os.path.isfile(p):
            os.remove(p)
        else:
            try:
                os.rmdir(p)
            except OSError as e:
                clear_path(p)
                os.rmdir(p)
