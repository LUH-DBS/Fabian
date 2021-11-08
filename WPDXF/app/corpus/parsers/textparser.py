from nltk.corpus import stopwords
from nltk.tokenize.nist import NISTTokenizer
from settings import Settings
from stats import Statistics

# nltk.download('stopwords', download_dir="/home/fabian/anaconda3/envs/ma/nltk_data")
# Valid strings are either a single character or number or a string without separators,
# that starts and ends with a character or a number.
# PATTERN = compile(
#     r"[\p{Latin}\p{N}][\p{Latin}\p{N}\p{P}]*[\p{Latin}\p{N}]|[\p{Latin}\p{N}]"
# )
# PATTERN = compile(
#     r"[\p{Latin}\p{N}](?:[\p{Latin}\p{N}]|[^\P{P}\p{Ps}\p{Pe}])*[\p{Latin}\p{N}]|[\p{Latin}\p{N}]"
# )


class TextParser:
    stopwords = set(stopwords.words("english"))

    def __init__(self) -> None:
        self.tokenizer = NISTTokenizer()
        self.max_token_len = Settings().MAX_TOKEN_LEN

    def tokenize(self, text_stream, ignore_stopwords: bool = True):

        text = text_stream.read().decode("utf-8")
        counter = {
            "total_tok": 0,
            "nostopword_tok": 0,
        }  # [ total_tokens, after_removed_stopwords ]

        def is_alnum_filter(token):
            for c in token:
                if c.isalnum():
                    return True
            return False

        def token_filter(token):
            if not is_alnum_filter(token):
                return False
            if ignore_stopwords:
                counter["total_tok"] += 1
                if token in self.stopwords:
                    return False
            counter["nostopword_tok"] += 1
            return True

        tokens = self.tokenizer.tokenize(text, lowercase=True)
        token_idx = 0
        for token in filter(token_filter, tokens):
            while len(token) > 0:
                yield (token[: self.max_token_len], token_idx)

                token = token[self.max_token_len :]
                token_idx += 1

        if ignore_stopwords:
            Statistics().update_stopword_eff(
                counter["total_tok"], counter["nostopword_tok"]
            )
