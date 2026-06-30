"""A tiny byte-level tokenizer with no external model or service."""

from __future__ import annotations


class ByteTokenizer:
    PAD = 0
    BOS = 1
    EOS = 2
    UNK = 3
    OFFSET = 4
    vocab_size = 260

    def encode(
        self, text: str, *, add_bos: bool = False, add_eos: bool = False
    ) -> list[int]:
        tokens = [byte + self.OFFSET for byte in text.encode("utf-8")]
        if add_bos:
            tokens.insert(0, self.BOS)
        if add_eos:
            tokens.append(self.EOS)
        return tokens

    def decode(self, tokens: list[int]) -> str:
        raw = bytes(
            token - self.OFFSET
            for token in tokens
            if self.OFFSET <= token < self.vocab_size
        )
        return raw.decode("utf-8", errors="replace")

