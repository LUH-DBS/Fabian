import logging
from collections import UserList, UserString
from itertools import chain, combinations, islice, product
from math import gcd
from typing import Any, Iterator, List, Tuple

logging.basicConfig(level=logging.DEBUG, filename="temp.log", filemode="w")
DBG = True

# Used for typing Only! See TextRegion, WebRegion for actual implementations
class Region(UserString):
    position = None

    def relative_position(self, other):
        # Specify in Region classes
        raise NotImplementedError


def learn(Q, args, num, do_cleanup):

    if isinstance(args, tuple):
        n, args = args[0], args[1:]
    else:
        n, args = args, tuple()

    logging.debug(
        f"\nlearn():\nQ: {Q}\nn: {n}\nargs: %s", "\n".join(map(str, enumerate(args)))
    )
    # if not Q:
    #     logging.warning("Q is an empty sequence, further evaluation skipped.")
    #     return StopIteration
    return n.learn(Q, *args, num=num, do_cleanup=do_cleanup)


class NonTerminal:
    # Specifies whether a cleanUp at the end of the learning phase is expected by the NonTerminal or not.
    # The cleanUp phase can still be omitted by passing do_cleanup=False for an individual learn process.
    # (A cleanUp will be done when cls_cleanup AND do_cleanup evaluates to True)
    # cls_cleanup = True

    def _call(self, state: Region):
        raise NotImplementedError

    def __call__(self, state: Region) -> Iterator:
        logging.debug(f"{self}.call\nstate: {state}")

        res = self._call(state)

        logging.debug(f"{self}.call (result)\n{res}\n")

        return res

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], *args, num, do_cleanup
    ) -> Iterator:
        raise NotImplementedError

    @classmethod
    def learn(
        cls, Q: List[Tuple[Region, List[Region]]], *args, num=None, do_cleanup=True
    ):

        # logging.debug(
        #     f"\n{cls}.learn\nQ: {Q}\nargs: %s", "\n".join(map(str, enumerate(args)))
        # )

        res = cls._learn(Q, *args, num=num, do_cleanup=do_cleanup)
        if cls.cls_cleanup and do_cleanup:
            res = cleanUp(res, Q)
        return islice(res, num)


class Chain(NonTerminal):
    cls_cleanup = False

    @classmethod
    def _learn(
        self, Q: List[Tuple[Region, List[Region]]], *P, num, do_cleanup
    ) -> Iterator:
        return chain(*(learn(Q, args, num=num, do_cleanup=do_cleanup) for args in P))


class Cond(NonTerminal):
    cls_cleanup = False

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], cond, arg0, arg1, num, do_cleanup
    ) -> Iterator:
        if cond(Q):
            return learn(Q, arg0, num=num, do_cleanup=do_cleanup)
        return learn(Q, arg1, num=num, do_cleanup=do_cleanup)


class T(NonTerminal):
    cls_cleanup = False

    def __init__(self, func, name=None) -> None:
        self.func = func

    def _call(self, state: Region):
        return self.func(state)

    @classmethod
    def _learn(cls, _, func, **kwargs) -> Iterator:
        yield T(func)


class Map(NonTerminal):
    cls_cleanup = True

    def __init__(self, F, S, transform_x=None) -> None:
        self.F = F
        self.S = S
        self.transform_x = transform_x or (lambda s, x: x)

    def _call(self, state: Region) -> List[Region]:
        return map(self.F, self.transform_x(state, self.S(state)))

    @classmethod
    def _learn(
        cls,
        Q: List[Tuple[Region, List[Region]]],
        F,
        S,
        learn_transform_x,
        transform_x,
        num,
        do_cleanup,
    ) -> Iterator:
        # S: Q -> Z
        # F: Z -> Y
        Z: List[Tuple[Region, Region]] = [cls.decompose(*q) for q in Q]

        Q1 = [(z, [y[j]]) for i, (q, y) in enumerate(Q) for j, z in enumerate(Z[i])]
        if learn_transform_x:
            Q1 = learn_transform_x(Q1)
        Q1 = [(z, y) for z, (y,) in Q1]
        P1 = learn(Q1, F, num=num, do_cleanup=do_cleanup)

        Q2 = [(q, Z[i]) for i, (q, _) in enumerate(Q)]
        P2 = learn(Q2, S, num=num, do_cleanup=do_cleanup)

        for i, p1 in enumerate(P1):
            for j, p2 in enumerate(P2):
                logging.debug(f"Map.learn (result: {i},{j})")
                yield cls(p1, p2, transform_x)

        # return (cls(*p, transform_x) for p in product(P1, P2))

    @classmethod
    def decompose(cls, state, Y):
        # Implement in subclasses
        raise NotImplementedError


class Merge(NonTerminal):
    cls_cleanup = True

    def __init__(self, A: list) -> None:
        self.A = A

    def _call(self, state: Region) -> List[Region]:
        return set.union(*map(lambda a: set(a(state)), self.A))

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], A, num, do_cleanup
    ) -> Iterator:

        _C = [
            [(state, c) for i in range(len(Y) + 1) for c in combinations(Y, len(Y) - i)]
            for state, Y in Q
        ]

        ALL_Y = set([y for _, Y in Q for y in Y])

        # # All possible combinations of example subsets
        X = []
        for states in product(*_C):
            # Drop states without examples
            states = [*filter(lambda s: len(s[1]) > 0, states)]
            if not states:
                continue
            X.append(states)
            p_iter = learn(states, A, num=None, do_cleanup=False)
            if next(p_iter, False):
                X.append(states)
        X.sort(key=lambda x: sum([len(_x) for _x in x]))

        T = sorted(
            partitions(X, ALL_Y, lambda x: [v for _x in x for v in _x[1]]), key=len,
        )

        logging.info("###Start: Learning with Clean Up###")

        for _X in T:
            _P = (learn(q, A, num=num, do_cleanup=do_cleanup) for q in _X)
            for p in product(*_P):
                yield Merge(p)


class FilterBool(NonTerminal):
    cls_cleanup = True

    def __init__(self, B, S) -> None:
        self.B = B
        self.S = S

    def _call(self, state: Region) -> List[Region]:
        return [*filter(self.S, self.B(state))]

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], B, S, num, do_cleanup
    ) -> Iterator:
        P1 = learn(Q, S, num=num, do_cleanup=do_cleanup)

        _Q = [(y, True) for _, Y in Q for y in Y]
        P2 = learn(_Q, B, num=num, do_cleanup=do_cleanup)

        return (FilterBool(*p) for p in product(P1, P2))


class FilterInt(NonTerminal):
    cls_cleanup = True

    def __init__(self, init, iter, S) -> None:
        assert iter > 0, "FilterInt cannot be initialized with a step size of 0."
        self.init = init
        self.iter = iter
        self.S = S

    def _call(self, state: Region) -> List[Region]:
        # (Iterator, start, stop, step)
        return self.S(state)[self.init :: self.iter]

    @classmethod
    def _learn(
        cls,
        Q: List[Tuple[Region, List[Region]]],
        S,
        transform_x=None,
        *,
        num,
        do_cleanup,
    ) -> Iterator:
        if transform_x:
            Q = transform_x(Q)
        cnt = 0
        for total, p1 in enumerate(learn(Q, S, num, do_cleanup)):
            keep_p = True

            init = float("inf")
            iter = 0
            for q, Y in Q:
                z = list(p1(q))
                if Y[0] in z:
                    idx0 = z.index(Y[0])
                else:
                    keep_p = False
                    break
                init = min(init, idx0)
                for i in range(len(Y) - 1):
                    idx1 = z.index(Y[i + 1])
                    t = idx1 - idx0
                    idx0 = idx1
                    iter = t if iter == 0 else gcd(iter, t)
            if keep_p:
                iter = 1 if iter == 0 else iter
                cnt += 1
                logging.debug(f"FilterInt Iteration {total} Yield {cnt}")
                yield FilterInt(init, iter, p1)


class Pair(NonTerminal):
    cls_cleanup = False

    def __init__(self, A, B) -> None:
        self.A = A
        self.B = B

    def _call(self, state: Region) -> Region:
        start, end = self.A(state), self.B(state)
        if start is None or end is None:
            return
        return state[start:end]

    @classmethod
    def _learn(
        cls, Q: List[Tuple[Region, List[Region]]], A, B, num, do_cleanup
    ) -> Iterator:
        Q = [(state, y.relative_position(state)) for state, y in Q]
        Q1, Q2 = zip(*(((_s, _y[0]), (_s, _y[1])) for _s, _y in Q))
        P1 = learn(Q1, A, num, do_cleanup)
        P2 = learn(Q2, B, num, do_cleanup)
        return (Pair(*p) for p in product(P1, P2))


def create_result_set(p, Q):
    return tuple(frozenset(p(s)) for s, _ in Q)


def subsumes(r1: Tuple[frozenset, ...], r2: Tuple[frozenset, ...]) -> bool:
    # p1 subsumes p2
    return all(r1[i] <= r2[i] for i in range(len(r1)))


def cleanUp(P, Q):
    logging.debug(f"\ncleanUp()\nP: {P}\nQ: {Q}")

    known_results = {}

    for p in P:
        result_set = create_result_set(p, Q)
        incl = True
        subsumed = []
        for kr in known_results:
            # If a known result subsumes the current result, drop it and continue with next p
            if subsumes(kr, result_set):
                incl = False
                break
            # If the current result subsumes a known result, save the known result as 'subsumed'.
            if subsumes(result_set, kr):
                subsumed.append(kr)
        # If the current result holds the conditions, add it to known results and remove all (now) subsumed results.
        if incl:
            known_results[result_set] = p
            for key in subsumed:
                known_results.pop(key)
    return iter(known_results.values())


def partitions(l: list, values, key=None):
    key = key or (lambda x: x)

    for i, item in enumerate(l):
        item_vals = set(key(item))
        if item_vals == values:
            yield [item]
        elif item_vals < values:
            subparts = partitions(l[i + 1 :], values - item_vals, key)
            for part in subparts:
                yield [item] + part


if __name__ == "__main__":

    class TP:
        def __init__(self, retval) -> None:
            self.retval = iter(retval)

        def __call__(self, arg):
            return next(self.retval)

    P = [TP([{0, 1, 2}, {0, 1}]), TP([{0, 1}, {0, 1}]), TP([{2, 3}, {0, 1}])]
    Q = [(None, None), (None, None)]
    print(list(cleanUp(P, Q)))

