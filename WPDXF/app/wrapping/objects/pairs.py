from corpus.parsers.textparser import TextParser


class Pair:
    def __init__(self, id, inp, out) -> None:
        self.id = id

        tp = TextParser()
        self.pair = (inp, out)

        inp_tok = tp.tokenize_str(inp)
        out_tok = tp.tokenize_str(out) if out else []
        self.tok = (inp_tok, out_tok)

    def __repr__(self) -> str:
        return str(self.pair)

    def __contains__(self, item) -> bool:
        return item in self.tokens()

    @property
    def inp(self):
        return self.pair[0]

    @property
    def out(self):
        return self.pair[1]

    @property
    def tok_inp(self):
        return self.tok[0]

    @property
    def tok_out(self):
        return self.tok[1]

    def tokens(self) -> set:
        return set(t for t, _ in self.tok[0] + self.tok[1])


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
