from gzip import GzipFile
from hashlib import sha1
from io import BytesIO
from os.path import isfile, join
from urllib.parse import quote

import requests
from warcio.recordloader import ArcWarcRecordLoader
from wpdxf.corpus.parsers.htmlparser import HTMLParser
from wpdxf.utils.settings import Settings
from wpdxf.utils.utils import compress_file, decompress_file


def search_index(url):
    url = quote(url)
    response = requests.get(
        "https://index.commoncrawl.org/CC-MAIN-2021-43-index",
        params={"url": url, "limit": 1, "output": "json"},
    )
    response.raise_for_status()
    return response.json()


def fetch_warc(filename, offset, length):
    response = requests.get(
        Settings().CC_DOMAIN + filename,
        params={"range": f"bytes={offset}-{offset + length - 1}"},
    )
    response.raise_for_status()
    gz = GzipFile(fileobj=BytesIO(response.content))
    return ArcWarcRecordLoader().parse_record_stream(gz)


def get_html(uri):
    uri_hash = sha1(uri.encode()).hexdigest()
    filepath = join(Settings().WARC_FILES, uri_hash)

    if isfile(filepath):
        return decompress_file(filepath)
    else:
        print(f"Retrieve HTML for {uri}")
        try:
            response = search_index(uri)
            warc = fetch_warc(
                response["filename"], int(response["offset"]), int(response["length"])
            )
        except requests.exceptions.HTTPError as e:
            print(e)
            return None
        raw_html = warc.content_stream().read()
        clean_html = HTMLParser(raw_html).clean_html
        compress_file(filepath, clean_html)
        return clean_html
