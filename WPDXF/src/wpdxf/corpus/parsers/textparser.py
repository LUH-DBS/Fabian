from nltk.corpus import stopwords
from nltk.tokenize.nist import NISTTokenizer
from wpdxf.utils.settings import Settings
from wpdxf.utils.stats import Statistics

# nltk.download('perluniprops')
# nltk.download('stopwords')


class TextParser:
    stopwords = set(stopwords.words("english"))

    def __init__(self) -> None:
        self.tokenizer = NISTTokenizer()
        self.max_token_len = Settings().MAX_TOKEN_LEN

    @staticmethod
    def is_alnum_filter(token):
        for c in token:
            if c.isalnum():
                return True
        return False

    def tokenize(self, text_stream, ignore_stopwords: bool = True):
        """This tokenizer is based on nltk.tokenize.nist.NISTTokenizer. 
        It split a given text into lowercase tokens and removes all tokens that:
        1) Do not contain any alpha-numeric (alnum) character (e.g.: punctuation, separators, ...)
        2) Are included in the english nltk.stopwords
        The tokens are enumerated afterwards.
        Automatically updates the statistics regarding 'stopword efficiency'.

        Note: 
            Tokens that are longer than MAX_TOKEN_LEN are split into multiple tokens 
            and treated as individual tokens.

        Args:
            text_stream (RawIOBase): A byte stream. It must be ensured that read() is implemented.
            ignore_stopwords (bool, optional): Specify whether stopwords should be removed or not. 
                Used for testing. Defaults to True.

        Yields:
            Tuple[str, int]: Token and its position in the tokenized text.
        """
        counter = {
            "total_tok": 0,
            "nostopword_tok": 0,
        }
        # counter: [ tokens_in_total, tokens_after_stopword_removal ]
        # tokens_in_total does not include non-alnum characters.

        def token_filter(token):
            if not self.is_alnum_filter(token):
                return False
            if ignore_stopwords:
                counter["total_tok"] += 1
                if token in self.stopwords:
                    return False
            counter["nostopword_tok"] += 1
            return True

        text = text_stream.read().decode("utf-8")
        tokens = self.tokenizer.tokenize(text, lowercase=True)

        # Iterate over all valid tokens
        token_idx = 0
        for token in filter(token_filter, tokens):
            while len(token) > 0:
                yield (token[: self.max_token_len], token_idx)

                token = token[self.max_token_len :]
                token_idx += 1

        # Update statistics at the end
        if ignore_stopwords:
            Statistics().update_stopword_eff(
                counter["total_tok"], counter["nostopword_tok"]
            )

    def tokenize_str(self, text_str: str, ignore_stopwords=True):
        def token_filter(token):
            if not self.is_alnum_filter(token):
                return False
            if ignore_stopwords:
                if token in self.stopwords:
                    return False
            return True

        tokens = self.tokenizer.tokenize(text_str, lowercase=True)
        result = []
        # Iterate over all valid tokens
        token_idx = 0
        for token in filter(token_filter, tokens):
            while len(token) > 0:
                result.append((token[: self.max_token_len], token_idx))

                token = token[self.max_token_len :]
                token_idx += 1
        return result
