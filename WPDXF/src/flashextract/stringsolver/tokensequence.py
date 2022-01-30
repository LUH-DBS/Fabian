from itertools import product


class TokenSeq(tuple):
    def convert(self):
        return "".join([t.convert() for t in self])


class STokenSeq(tuple):
    def intersect(self, other):
        if len(self) != len(other):
            return

        seq = []
        for i in range(len(self)):
            tmp = self[i] & other[i]
            if not tmp:
                return STokenSeq()
            seq.append(tmp)

        return STokenSeq(seq)

    def product(self):
        return map(TokenSeq, product(*self))
