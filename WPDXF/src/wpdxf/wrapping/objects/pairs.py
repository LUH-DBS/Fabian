from dataclasses import InitVar, dataclass, field
from typing import Set, Tuple

from wpdxf.corpus.parsers.textparser import TextParser


def tokenized(input: str, output: str = None, ignore_stopwords=False):
    tp = TextParser()

    inp = tp.tokenize_str(input, ignore_stopwords)
    if inp:
        inp, _ = zip(*inp)
        inp = " ".join(inp)
    else:
        inp = ""

    if output is None:
        return inp

    out = tp.tokenize_str(output, ignore_stopwords)
    if out:
        out, _ = zip(*out)
        out = " ".join(out)
    else:
        out = ""

    return inp, out


@dataclass(frozen=True)
class Pair:
    inp: str
    out: str

    tp: InitVar[TextParser] = TextParser()

    tok_inp: Tuple[Tuple[str, int], ...] = field(init=False, compare=False, repr=False)
    tok_out: Tuple[Tuple[str, int], ...] = field(init=False, compare=False, repr=False)
    tokens: Set[str] = field(
        init=False, compare=False, repr=False,
    )

    def __post_init__(self, tp):
        object.__setattr__(self, "tok_inp", self.tp.tokenize_str(self.inp))
        object.__setattr__(self, "tok_out", self.tp.tokenize_str(self.out))
        object.__setattr__(
            self, "tokens", set(t for t, _ in self.tok_inp + self.tok_out)
        )

    def __contains__(self, item: str) -> bool:
        return item in self.tokens

    @property
    def pair(self) -> Tuple[str, str]:
        return (self.inp, self.out)

    @property
    def tok(self) -> Tuple[Tuple[str, int], Tuple[str, int]]:
        return (self.tok_inp, self.tok_out)


class Example(Pair):
    def __init__(self, inp, out) -> None:
        if out is None:
            raise ValueError("The output of an example cannot be None.")
        super().__init__(inp, out)


class Query(Pair):
    def __init__(self, inp, *args) -> None:
        super().__init__(inp, None)


# if __name__ == "__main__":
#     e = Example("This is a test input.", "This is the test output.")
#     print(e)
#     print(e.tok)
#     print(e.pair)
#     print(e.tokens)

#     e = Query("This is a test input.")
#     e2 = Query("This is a test input.")
#     assert e == e2
#     print(e)
#     print(e.tok)
#     print(e.pair)
#     print(e.tokens)

#     print("this" in e)
#     print("input" in e)
