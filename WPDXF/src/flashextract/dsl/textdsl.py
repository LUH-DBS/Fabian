from collections import UserString
from dataclasses import dataclass
from functools import partial
from itertools import combinations
from typing import Iterator, List, NamedTuple, Tuple

from flashextract.dsl.basic import (DBG, Chain, FilterBool, FilterInt, Map,
                                    Merge, NonTerminal, Pair, Region, T,
                                    cleanUp, learn)
from flashextract.stringsolver.dsl import (AbsPos, PosSeq, RegPos,
                                           generate_patterns)
from flashextract.stringsolver.tokens import (LIST_NON_EMPTY_TOKENS, Token,
                                              positions_ending_with,
                                              positions_starting_with)


class LinesMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        # print("LinesMap.decompose")
        lines = []
        for sequence in Y:
            seq_low, seq_high, offset = sequence.relative_position(state)
            line_low = state.seq.rfind("\n", 0, seq_low) + 1
            line_high = state.seq.find("\n", seq_high)
            if line_high == -1:
                line_high = len(state)
            line = state[line_low:line_high]
            assert sequence in line, f"Sequence: {sequence}, Line: {line}"
            lines.append(line)
        # print("LinesMap lines", lines)
        return lines


class StartSeqMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        starts = []
        for sequence in Y:
            # print("SSM.decompose", repr(state), repr(sequence))
            seq_low, *_ = sequence.relative_position(state)
            starts.append(state[seq_low:])
        return starts


class EndSeqMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        endings = []
        for sequence in Y:
            _, seq_high, _ = sequence.relative_position(state)
            endings.append(state[:seq_high])
        return endings


class LineSplit(NonTerminal):
    cls_cleanup = False

    def _call(self, state: Region) -> List[Region]:
        lines = []
        start = 0
        while True:
            end = state.seq.find("\n", start)
            if end < 0:
                if start < len(state):
                    lines.append(state[start:])
                break
            lines.append(state[start:end])
            start = end + 1
        return lines

    @classmethod
    def _learn(cls, Q: List[Tuple[Region, List[Region]]], **_) -> Iterator:
        yield LineSplit()


# Predicates
class Predicate(NonTerminal):
    cls_cleanup = False

    def __init__(self, func, name=None) -> None:
        self.func = func
        self.name = name

    def __repr__(self) -> str:
        return self.name

    def _call(self, state: Region) -> bool:
        return self.func(s=str(state))

    @classmethod
    def _learn(cls, Q: List[Tuple[Region, List[Region]]], **kwargs) -> Iterator:
        # tautology
        yield Predicate(lambda s: True, "Tautology")

        # startswith
        func = lambda p, s: positions_starting_with(p, s) == [0]
        for pattern in generate_patterns(startswith=(Token.StartTok,)):
            if all(func(pattern, str(s)) for s, _ in Q):
                yield Predicate(partial(func, p=pattern), f"StartsWith {pattern}")

        # endswith
        func = lambda p, s: positions_ending_with(p, s) == [len(s)]
        for pattern in generate_patterns(endswith=(Token.EndTok,)):
            if all(func(pattern, str(s)) for s, _ in Q):
                yield Predicate(partial(func, p=pattern), f"EndsWith {pattern}")

        # contains
        for pattern in generate_patterns():
            k = None
            for s, _ in Q:
                _len = len(positions_starting_with(pattern, str(s)))
                if k is None:
                    k = _len
                if k != _len or k == 0:
                    break
            else:
                yield Predicate(
                    lambda s: len(positions_starting_with(pattern, str(s))) == k,
                    f"Contains {k} {pattern}",
                )
        # TODO: pred starts/endswith, contains; succ starts/endswith, contains


class TextDSL:
    def startseq_to_pos(Q):
        return [(s, [y.relative_position(s)[0] for y in Y]) for s, Y in Q]

    def pos_to_startseq(state, x):
        return [state[k:] for k in x]

    def endseq_to_pos(Q):
        return [(s, [y.relative_position(s)[1] for y in Y]) for s, Y in Q]

    def pos_to_endseq(state, x):
        return [state[:k] for k in x]

    Pos = (Chain, AbsPos, RegPos)
    BLS = (FilterBool, Predicate, LineSplit)
    LS = (FilterInt, BLS)
    PS0 = (
        Chain,
        (LinesMap, Pos, LS, startseq_to_pos, None),
        (FilterInt, PosSeq, startseq_to_pos),
    )
    PS1 = (
        Chain,
        (LinesMap, Pos, LS, endseq_to_pos, None),
        (FilterInt, PosSeq, endseq_to_pos),
    )
    SS = (
        Chain,
        (LinesMap, (Pair, Pos, Pos), LS, None, None),
        (StartSeqMap, (Pair, (T, lambda x: 0), Pos), PS0, None, pos_to_startseq,),
        (EndSeqMap, (Pair, Pos, (T, lambda x: len(x))), PS1, None, pos_to_endseq),
    )

    N1 = (Merge, SS)
    N2 = (Pair, Pos, Pos)

# if __name__ == "__main__":
#     t1 = TextRegion("Test", 0)
#     t2 = TextRegion("Test", 0)
#     t3 = TextRegion("Test", 1)
#     t4 = TextRegion("ABC", 0)

#     assert t1 == t2
#     assert t1 != t3
#     assert t1 != t4
