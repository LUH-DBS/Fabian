from collections import UserDict, defaultdict
from copy import deepcopy
from itertools import combinations, product
from typing import Dict, Iterable, Iterator, List, Set, Tuple

from flashextract.dsl.basic import DBG, NonTerminal, Region
from flashextract.stringsolver.tokens import (LIST_NON_EMPTY_TOKENS,
                                              RepeatedNonToken, Token,
                                              first_position_ending_with,
                                              positions_ending_with,
                                              positions_of_tokens,
                                              positions_starting_with)
from flashextract.stringsolver.tokensequence import STokenSeq, TokenSeq


def absolute_position(k: int, x: str):
    if k < 0:
        k += len(x)
    if not 0 <= k < len(x):
        return None
    return k


class AbsPos(NonTerminal):
    cls_cleanup = False

    def __init__(self, k) -> None:
        self.k = k

    def _call(self, state: Region) -> int:
        return absolute_position(self.k, state)

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], *args, num, do_cleanup
    ) -> Iterator:
        def positions(region: Region, k: int) -> Set[int]:
            # Calculate absolute positions of a single state
            if k is None:
                return set()
            pos = {k}
            rel_k = k - len(region)
            if rel_k != 0:
                pos.add(rel_k)
            return pos

        # Calculate common absolute positions for all states
        pos = set.intersection(*map(lambda x: positions(*x), Q))
        return map(AbsPos, pos)


class RegPos(NonTerminal):
    cls_cleanup = False

    def __init__(self, r1, r2, k) -> None:
        self.r1 = r1
        self.r2 = r2
        self.k = k

    def _call(self, state: Region) -> int:
        pos = set()
        for r1, r2, k in product(self.r1.product(), self.r2.product(), self.k):
            res1 = positions_ending_with(r1, str(state))
            res2 = positions_starting_with(r2, str(state))
            intersect = sorted(set(res1) & set(res2))
            k = absolute_position(k, intersect)
            if k is not None:
                pos.add(intersect[k])
        if len(pos) == 1:
            return pos.pop()

    @classmethod
    def _learn(cls, Q: List[Tuple[Region, List[Region]]], **kwargs) -> Iterator:
        pos = None
        for region, k in Q:
            if k is None:
                return set()
            new_pos = [
                RegPos(r1, r2, _k) for r1, r2, _k in generate_positions(str(region), k)
            ]
            if pos is None:
                pos = new_pos
            else:
                pos = RegPos.intersect_all(pos, new_pos)
            if not pos:
                return []
        return (p for p in pos)

    @staticmethod
    def intersect_all(rp1s, rp2s):
        return set(map(lambda x: RegPos.intersect(*x), product(rp1s, rp2s))) - {None}

    @staticmethod
    def intersect(rp1, rp2):
        # Intersection of both position sets
        nk = rp1.k & rp2.k
        if not nk:
            return
        # "IntersectRegex(r1, r1_)"
        nr1 = rp1.r1.intersect(rp2.r1)
        if not nr1:
            return
        # "IntersectRegex(r2, r2_)"
        nr2 = rp1.r2.intersect(rp2.r2)
        if not nr2:
            return
        return RegPos(nr1, nr2, nk)


class PosSeq(NonTerminal):
    cls_cleanup = False

    def __init__(self, r1, r2) -> None:
        self.r1 = r1
        self.r2 = r2

    def _call(self, state: Region) -> List[int]:
        pos = set()
        for r1, r2 in product(self.r1.product(), self.r2.product()):
            res1 = positions_ending_with(r1, str(state))
            res2 = positions_starting_with(r2, str(state))
            intersect = set(res1) & set(res2)
            pos |= intersect
        return sorted(pos)

    @classmethod
    def _learn(cls, Q: List[Tuple[Region, List[int]]], **kwargs) -> Iterator:
        pos = None
        for region, K in Q:
            for k in K:
                assert isinstance(k, int)
                new_pos = [
                    PosSeq(r1, r2) for r1, r2, _ in generate_positions(str(region), k)
                ]
                if pos is None:
                    pos = new_pos
                else:
                    pos = PosSeq.intersect_all(pos, new_pos)
                if not pos:
                    return []
        return (p for p in pos)

    @staticmethod
    def intersect_all(rp1s, rp2s):
        return set(map(lambda x: PosSeq.intersect(*x), product(rp1s, rp2s))) - {None}

    @staticmethod
    def intersect(rp1, rp2):
        nr1 = rp1.r1.intersect(rp2.r1)
        if not nr1:
            return
        nr2 = rp1.r2.intersect(rp2.r2)
        if not nr2:
            return
        return PosSeq(nr1, nr2)


class IParts(UserDict):
    list_tokens = LIST_NON_EMPTY_TOKENS

    def __init__(self, s: str) -> None:
        position_groups = defaultdict(list)
        for token in self.list_tokens:
            positions = positions_of_tokens(token, s)
            if positions:
                position_groups[positions].append(token)

        # self.s = s
        super().__init__({t[0]: set(t) for t in position_groups.values()})

    def __getitem__(self, key):
        if key in (Token.StartTok, Token.EndTok):
            return {key}
        return super().__getitem__(key)

    def reps(self):
        return self.keys()


def compute_tokenseq(s: str, token_set: set):
    # All indices are described in a pythonic way -> start - inclusive, end - exclusive
    token_sequences: Dict[
        (int, int), Set[(TokenSeq, (int, int))]
    ] = {}  # A mapping of (start, end) values to all TokenSeq matching this substring.

    def add_mapping(i: int, j: int, seq: TokenSeq, idx: Tuple[int, int]):
        # if not seq or any(_t != RepeatedNonToken.NonDotTok for _t in seq): ...
        if seq and all(_t == RepeatedNonToken.NonDotTok for _t in seq):
            return
        values = token_sequences.get((i, j), set())
        values.add((seq, idx))
        token_sequences[(i, j)] = values

    token_positions = {_t: positions_of_tokens(_t, s) for _t in token_set}

    token_start_map = defaultdict(list)
    # start_index -> TokenSequences starting at start_index
    for item in token_positions.items():
        for start, _ in item[1]:
            token_start_map[start] += [item]

    token_start_end_map = defaultdict(dict)
    # start_index -> TokenSequence -> First end_index
    for token, borders in token_positions.items():
        for start, _ in borders:
            token_start_end_map[start].update(
                {token: start + first_position_ending_with(token, s, start)}
            )

    # enumerate token sequences of length 0
    indices = tuple([(i, i) for i in range(len(s) + 1)])
    for i in range(len(s) + 1):
        add_mapping(i, i, TokenSeq(), indices)

    # enumerate token sequences of length 1
    for i in range(0, len(s)):
        for token, index in token_start_map[i]:
            if token not in (Token.StarTok, Token.EndTok):
                end = token_start_end_map[i][token]
                if end > i:
                    add_mapping(i, end, TokenSeq([token]), index)

    def append_token_sequences(size: int):
        current_mapping = deepcopy(token_sequences)
        # Iterate all sequence sets that have not already reached the end
        for (start, end), tokenseq_set in current_mapping.items():
            if end == len(s):
                continue

            # Iterate all sequences having 'size' elements
            # and check for possibilities to increase sequences to 'size + 1'
            for tokenseq, _ in filter(lambda x: len(x[0]) == size, tokenseq_set):
                contiguous_tokens = token_start_map[end]
                for token, _ in contiguous_tokens:
                    if token != tokenseq[-1]:
                        _end = token_start_end_map[end][token]
                        _tokenseq = TokenSeq(tokenseq + (token,))
                        _position = positions_of_tokens(_tokenseq, s)
                        add_mapping(start, _end, _tokenseq, _position)

    # enumerate token sequences of length 2
    append_token_sequences(1)

    # enumerate token sequences of length 3
    append_token_sequences(2)

    current_mapping = deepcopy(token_sequences)
    for (start, end), tokenseq_set in current_mapping.items():
        for tokenseq, borders in tokenseq_set:
            if start == 0:
                add_mapping(
                    start, end, TokenSeq((Token.StartTok,) + tokenseq), borders[:1]
                )
            if end == len(s):
                add_mapping(
                    start, end, TokenSeq(tokenseq + (Token.EndTok,)), borders[-1:]
                )

    return token_sequences


def matching_tokenseq(s: str, k: int, token_set: set):
    sequences = compute_tokenseq(s, token_set)
    for k1 in map(lambda i: k - i, range(k + 1)):
        for k2 in range(k, len(s) + 1):
            for tok1, _ in sequences.get((k1, k), []):
                res1 = positions_ending_with(tok1, s)
                for tok2, _ in sequences.get((k, k2), []):
                    res2 = positions_starting_with(tok2, s)
                    yield (k1, k2, tok1, tok2, set(res1) & set(res2))


def generate_patterns(min_len=0, max_len=3, startswith=None, endswith=None):
    startswith = startswith or tuple()
    endswith = endswith or tuple()
    for i in range(min_len, max_len + 1):
        for c in combinations(LIST_NON_EMPTY_TOKENS, i):
            yield TokenSeq(startswith + c + endswith)


def generate_positions(s: str, k: int):
    iparts = IParts(s)
    token_set = iparts.reps()
    for _, _, r1, r2, intersections in matching_tokenseq(s, k, token_set):
        if k not in intersections:
            continue

        r1p = generate_regex(r1, iparts)
        r2p = generate_regex(r2, iparts)
        c = sorted(intersections).index(k)

        yield (r1p, r2p, {c, -(len(intersections) - c)})


def generate_regex(r: TokenSeq, ip: IParts):
    return STokenSeq([*map(lambda t: ip[t], r)])
