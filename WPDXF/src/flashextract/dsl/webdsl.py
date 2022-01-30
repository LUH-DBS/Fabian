import logging
from typing import Iterator, List, Tuple

from flashextract.dsl.basic import (Chain, Cond, FilterInt, Map, Merge,
                                    NonTerminal, Pair, Region, T)
from flashextract.dsl.regions import WebRegion
from flashextract.stringsolver.dsl import AbsPos, PosSeq, RegPos
from lxml.etree import _Element


def get_xpath(node):
    if node is None:
        return
    try:
        return node.getroottree().getpath(node)
    except AttributeError:
        return get_xpath(node.getparent())


class XPaths(NonTerminal):
    cls_cleanup = False

    def __init__(self, _xpath) -> None:
        self._xpath = _xpath

    @classmethod
    def _learn(cls, Q: List[Tuple[Region, List[Region]]], **_) -> Iterator:
        example_xpaths = []
        for region, examples in Q:
            examples = [e.node for e in examples]
            if region.node.getparent() is None:  # "ALL"/root
                start = 0
            else:
                start = len(get_xpath(region.node))

            example_xpaths.extend(
                [get_xpath(e)[start + 1 :].split("/") for e in examples]
            )

        if not example_xpaths:
            return []

        min_len = min(map(len, example_xpaths))
        xpath = "."

        for i in range(min_len):
            tag = example_xpaths[0][i]
            if all(ex[i] == tag for ex in example_xpaths):
                xpath += "/" + tag
            else:
                xpath += "/*"

        yield XPaths(xpath)

    def _call(self, state: Region) -> List[Region]:
        logging.debug(self._xpath)
        return state.xpath(self._xpath)


class SeqPairMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        return [WebRegion(y.node, y.node.text, 0) for y in Y]


class StartSeqMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        starts = []
        for y in Y:
            seq_region = WebRegion(y.node, y.node.text, 0)
            seq_low, *_ = y.relative_position(state)
            starts.append(seq_region[seq_low:])
        return starts


class EndSeqMap(Map):
    @classmethod
    def decompose(cls, state, Y):
        ends = []
        for y in Y:
            seq_region = WebRegion(y.node, y.node.text, 0)
            _, seq_high, _ = y.relative_position(state)
            ends.append(seq_region[:seq_high])
        return ends


class WebDSL:
    def startseq_to_pos(Q):
        return [(s, [y.relative_position(s)[0] for y in Y]) for s, Y in Q]

    def pos_to_startseq(state, x):
        return [state[k:] for k in x]

    def endseq_to_pos(Q):
        return [(s, [y.relative_position(s)[1] for y in Y]) for s, Y in Q]

    def pos_to_endseq(state, x):
        return [state[:k] for k in x]

    Pos = (Chain, AbsPos, RegPos)
    ES = (FilterInt, XPaths)
    PS0 = (FilterInt, PosSeq, startseq_to_pos)
    PS1 = (FilterInt, PosSeq, endseq_to_pos)
    SS = (
        Chain,
        # (SeqPairMap, (Pair, Pos, Pos), ES, None, None),
        # (StartSeqMap, (Pair, (T, lambda x: 0), Pos), PS0, None, pos_to_startseq),
        (EndSeqMap, (Pair, Pos, (T, lambda x: len(x))), PS1, None, pos_to_endseq),
    )
    NS = XPaths
    N2 = (Chain, XPaths, (Pair, Pos, Pos))
    # N1 = (Chain, (Merge, NS), (Merge, SS))

    N1 = (
        Cond,
        lambda q: not all(y.has_sequence() for _, Y in q for y in Y),
        (Merge, NS),
        (Merge, SS),
    )

