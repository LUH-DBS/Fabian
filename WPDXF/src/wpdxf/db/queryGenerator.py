import logging
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from wpdxf.utils.settings import Settings
from wpdxf.wrapping.objects.pairs import Example, Pair, Query


def _tuple_interval(t, named: bool = False) -> str:
    if named:
        return ", ".join(f"%({token})s" for token in t)
    else:
        return ("%s, " * len(t))[:-2]


__SESSION_TYPES__ = ("postgres",)  # ("postgres", "vertica") "vertica" deprecated


class QueryExecutor:
    def __init__(self, session_type="postgres", max_rel_tf: float = None) -> None:
        assert session_type in __SESSION_TYPES__
        if session_type == "postgres":
            from wpdxf.db.PostgresDBSession import PostgresDBSession

            self.session = PostgresDBSession()
        # elif session_type == "vertica":
        #     from db.VerticaDBSession import VerticaDBSession
        #     session = VerticaDBSession()

        self.max_abs_tf = Settings().MAX_CORPUS_FREQ
        self.max_rel_tf = max_rel_tf or 0.01

        self.token_dict = {}

    def update_token_dict(self, tokens: Set[str]) -> Set[str]:
        def rel_tf(term_freq):
            return term_freq / self.max_abs_tf

        tokens -= set(self.token_dict)
        if not tokens:
            return set()
        _interval = _tuple_interval(tokens)
        stmt = f"SELECT token, tokenid, COUNT(1) as cnt FROM (SELECT * FROM tokens WHERE token IN ({_interval})) S JOIN token_uri_mapping USING(tokenid) GROUP BY tokenid, token"
        with self.session.execute(stmt, tuple(tokens)) as cur:
            for token, tokenid, cnt in cur:
                tokens.remove(token)
                if rel_tf(cnt) < self.max_rel_tf:
                    self.token_dict[token] = tokenid
        return tokens

    def remove_unresolved_pairs(self, pairs: List[Pair], unknown_tokens: Set[str]):
        for pair in pairs.copy():
            if pair.tokens & unknown_tokens:
                pairs.remove(pair)

    def create_masks(self, pairs: List[Pair]):
        def _mask(tokens):
            m = tuple(
                (self.token_dict[token], pos)
                for token, pos in tokens
                if token in self.token_dict
            )
            return self.drop_offset(m)

        masks = []
        for pair in pairs:
            mask = (_mask(pair.tok_inp),)
            if isinstance(pair, Example):
                mask += (_mask(pair.tok_out),)
            masks.append(mask)
        return masks

    def create_query(self, masks):
        token_pairs = []
        total_tokens = 0
        for i, pair_masks in enumerate(masks):
            pair_tokens = tuple(token for mask in pair_masks for token, _ in mask)
            total_tokens += len(pair_tokens)
            if pair_tokens:
                token_pairs.append((i, pair_tokens))
        stmt = " UNION ALL ".join(
            [
                f"""\
(SELECT tokenid, position, uri, {i}::integer FROM(
    SELECT tokenid, position, uriid 
    FROM token_uri_mapping
    WHERE tokenid IN ({_tuple_interval(tokens, True)})
    ORDER BY uriid, position
) S JOIN uris USING(uriid))"""
                for i, tokens in token_pairs
            ]
        )
        logging.info(stmt)
        logging.info(f"Total Tokens: {total_tokens}")
        stmt_dict = {str(token): token for _, tokens in token_pairs for token in tokens}
        return stmt, stmt_dict

    def yield_partition(self, cursor):
        key = None
        for tokenid, position, *_key in cursor:
            if key is None:  # Initial value
                key = _key
                partition = [(tokenid, position)]
            elif key != _key:  # New partition
                yield key, partition
                key = _key
                partition = [(tokenid, position)]
            else:  # Same partition
                partition.append((tokenid, position))
        yield key, partition

    def drop_offset(self, window: List[Tuple[int, int]]):
        if not window:
            return window
        offset = window[0][1]
        return tuple((tok, pos - offset) for tok, pos in window)

    def filter_query_result(
        self, stmt: str, stmt_dict: dict, pairs: List[Pair], masks: list
    ) -> Dict[str, List[Pair]]:
        def contains_pair(matches, pair) -> bool:
            return len(matches) == 1 and isinstance(pair, Query) or len(matches) == 2

        url_dict = defaultdict(list)
        with self.session.execute(stmt, stmt_dict) as cur:
            # print(cur.query.decode())
            for (url, pair_idx), partition in self.yield_partition(cur):
                matches = set()
                pair = pairs[pair_idx]

                pair_masks = tuple(enumerate(masks[pair_idx]))
                max_size = max(len(mask) for _, mask in pair_masks)
                min_size = min(len(mask) for _, mask in pair_masks)

                for i in range(len(partition) - min_size + 1):
                    window = partition[i : i + max_size]
                    if not window:
                        continue
                    window = self.drop_offset(window)
                    for mask_idx, mask in pair_masks:
                        if window[: len(mask)] == mask:
                            matches.add(mask_idx)
                    if contains_pair(matches, pair):
                        url_dict[url].append(pair)
                        break
        return dict(url_dict)

    def query_pairs(self, pairs: List[Pair]) -> Dict[str, List[Pair]]:
        tokens = set.union(*map(lambda x: x.tokens, pairs), set())
        unknown_tokens = self.update_token_dict(tokens)

        if unknown_tokens:
            self.remove_unresolved_pairs(pairs, unknown_tokens)

        if not pairs:
            return {}

        masks = self.create_masks(pairs)

        stmt, stmt_dict = self.create_query(masks)
        return self.filter_query_result(stmt, stmt_dict, pairs, masks)
