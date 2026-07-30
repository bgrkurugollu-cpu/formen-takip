
from __future__ import annotations

TURKISH_ALPHABET = "abcçdefgğhıijklmnoöpqrsştuüvwxyz"

_UPPER_TO_LOWER = {
    "I": "ı",
    "İ": "i",
}

_RANK = {char: index for index, char in enumerate(TURKISH_ALPHABET)}


def _char_rank(char: str) -> int:
    rank = _RANK.get(char)
    return rank if rank is not None else ord(char) - 0x110000


def turkish_lower(value: str) -> str:
    return "".join(_UPPER_TO_LOWER.get(char, char) for char in value).lower()


def turkish_sort_key(value: str) -> tuple[int, ...]:
    return tuple(_char_rank(char) for char in turkish_lower(value))
