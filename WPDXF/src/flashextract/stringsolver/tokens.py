from enum import Enum
from typing import List, Tuple, Union

import regex

PLUS = "{1,1000}"


class Token(Enum):
    HyphenTok = r"-"
    DotTok = r"\."
    SemiColonTok = r";"
    ColonTok = r":"
    CommaTok = r","
    Backslash = r"\\"
    SlashTok = r"/"
    LeftParenTok = r"\("
    RightParenTok = r"\)"
    LeftBracketTok = r"\["
    RightBracketTok = r"\]"
    LeftBraceTok = r"\{"
    RightBraceTok = r"\}"
    PercentageTok = r"%"
    HatTok = r"\^"
    UnderscoreTok = r"_"
    EqSignTok = r"="
    PlusTok = r"\+"
    StarTok = r"\*"
    AndTok = r"&"
    AtTok = r"@"
    DollarTok = r"\$"
    QuestionTok = r"\?"
    QuoteTok = r'"'
    PoundTok = r"#"
    ExclamationTok = r"!"
    SingleQuoteTok = r"'"
    LessTok = r"<"
    RightTok = r">"
    TildeTok = r"~"
    BackTickTok = r"`"
    EndTok = r"\Z"
    StartTok = r"\A"

    def convert(self):
        return f"{self.value}"


class RepeatedToken(Enum):
    UpperTok = r"A-Z"
    NumTok = r"0-9"
    LowerTok = r"a-z"
    AlphaTok = r"A-Za-z"
    AlphaNumTok = r"A-Za-z0-9"
    SpaceTok = r" "

    def convert(self):
        return f"(?<=[^{self.value}]|^)[{self.value}]{PLUS}(?=[^{self.value}]|$)"


class RepeatedNonToken(Enum):
    NonUpperTok = "A-Z"
    NonNumTok = "0-9"
    NonLowerTok = "a-z"
    NonAlphaTok = "A-Za-z"
    NonAlphaNumTok = "A-Za-z0-9"
    NonSpaceTok = r" "
    NonDotTok = r"."

    def convert(self):
        return f"(?<=[{self.value}]|^)[^{self.value}]{PLUS}(?=[{self.value}]|$)"


LIST_NON_EMPTY_TOKENS = (
    list(RepeatedToken)
    + list(RepeatedNonToken)
    + list(set(Token) - {Token.StartTok, Token.EndTok})
)
LIST_TOKENS = [Token.StarTok, Token.EndTok] + LIST_NON_EMPTY_TOKENS


def positions_of_tokens(tokens, s: str) -> Tuple[Tuple[int, int]]:
    starts = positions_starting_with(tokens, s)
    endings = positions_ending_with(tokens, s)
    return tuple(zip(starts, endings))


def positions_starting_with(tokens, s: str) -> List[int]:
    r = convert_regex(tokens, starting=True)
    return [_m.start() for _m in r.finditer(s)]


def positions_ending_with(tokens, s: str) -> List[int]:
    r = convert_regex(tokens, starting=False)
    return [_m.start() for _m in r.finditer(s)]


def first_position_ending_with(token, s: str, start: int) -> int:
    s = s[start:]
    r = convert_regex(token, starting=False)

    match = r.search(s)
    return match.start(0) if match else len(s)


def convert_regex(
    r: Union[Token, RepeatedToken, RepeatedNonToken], starting: bool
) -> regex.Pattern:
    return regex.compile(f"(?{(not starting)*'<'}={r.convert()})")
