from wpdxf.corpus.parsers.textparser import TextParser


class Pair:
    _tp = TextParser()

    def __init__(self, id, inp, out) -> None:
        self.id = id

        self.inp = inp
        self.out = out

        self.tok_inp = self._tp.tokenize_str(inp)
        self.tok_out = self._tp.tokenize_str(out) if out else []

    def __repr__(self) -> str:
        return str(self.pair)

    def __contains__(self, item) -> bool:
        return item in self.tokens()

    @property
    def pair(self) -> tuple:
        return (self.inp, self.out)

    @property
    def tok(self) -> tuple:
        return (self.tok_inp, self.tok_out)

    def tokens(self) -> set:
        return set(t for t, _ in self.tok_inp + self.tok_out)


class Example(Pair):
    def __init__(self, id, inp, out) -> None:
        if out is None:
            raise ValueError("The output of an example cannot be None.")
        super().__init__(id, inp, out)


class Query(Pair):
    def __init__(self, id, inp, *args) -> None:
        super().__init__(id, inp, None)


if __name__ == "__main__":
    e = Example(0, "This is a test input.", "This is the test output.")
    print(e)
    print(e.tok)
    print(e.pair)
    print(e.tokens())

    e = Query(0, "This is a test input.")
    print(e)
    print(e.tok)
    print(e.pair)
    print(e.tokens())

    print("this" in e)
    print("input" in e)
