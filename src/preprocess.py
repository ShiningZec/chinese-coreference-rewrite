import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int


def split_sentences(text: str) -> list[str]:
    """Split Chinese text into sentence-like segments."""
    parts = re.split(r"(?<=[。！？!?])", text)
    return [part.strip() for part in parts if part.strip()]


def simple_tokenize(text: str) -> list[Token]:
    """Tokenize text with simple character and phrase grouping."""
    tokens: list[Token] = []
    pattern = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+|[^\s]")
    for match in pattern.finditer(text):
        tokens.append(Token(match.group(), match.start(), match.end()))
    return tokens

