"""Decoder-only Transformer language model built with plain PyTorch."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class ModelConfig:
    vocab_size: int = 260
    context_length: int = 512
    d_model: int = 384
    n_heads: int = 6
    n_layers: int = 6
    dropout: float = 0.1

    def to_dict(self) -> dict:
        return asdict(self)


class CausalSelfAttention(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        if config.d_model % config.n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads")

        self.n_heads = config.n_heads
        self.head_size = config.d_model // config.n_heads
        self.dropout = config.dropout
        self.qkv = nn.Linear(config.d_model, 3 * config.d_model, bias=False)
        self.projection = nn.Linear(config.d_model, config.d_model, bias=False)
        self.residual_dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)

        def split_heads(tensor: torch.Tensor) -> torch.Tensor:
            return tensor.view(batch, length, self.n_heads, self.head_size).transpose(1, 2)

        q, k, v = map(split_heads, (q, k, v))
        attended = F.scaled_dot_product_attention(
            q,
            k,
            v,
            dropout_p=self.dropout if self.training else 0.0,
            is_causal=True,
        )
        attended = attended.transpose(1, 2).contiguous().view(batch, length, width)
        return self.residual_dropout(self.projection(attended))


class FeedForward(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(config.d_model, 4 * config.d_model),
            nn.GELU(),
            nn.Linear(4 * config.d_model, config.d_model),
            nn.Dropout(config.dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class TransformerBlock(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.attention_norm = nn.LayerNorm(config.d_model)
        self.attention = CausalSelfAttention(config)
        self.feed_forward_norm = nn.LayerNorm(config.d_model)
        self.feed_forward = FeedForward(config)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attention(self.attention_norm(x))
        return x + self.feed_forward(self.feed_forward_norm(x))


class LocalChatbot(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.position_embedding = nn.Embedding(config.context_length, config.d_model)
        self.dropout = nn.Dropout(config.dropout)
        self.blocks = nn.ModuleList(
            TransformerBlock(config) for _ in range(config.n_layers)
        )
        self.final_norm = nn.LayerNorm(config.d_model)
        self.output = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.output.weight = self.token_embedding.weight
        self.apply(self._initialize_weights)

    @staticmethod
    def _initialize_weights(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
        if isinstance(module, nn.Linear) and module.bias is not None:
            nn.init.zeros_(module.bias)

    def forward(
        self, tokens: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _, length = tokens.shape
        if length > self.config.context_length:
            raise ValueError(
                f"Sequence length {length} exceeds context length "
                f"{self.config.context_length}"
            )

        positions = torch.arange(length, device=tokens.device)
        x = self.token_embedding(tokens) + self.position_embedding(positions)
        x = self.dropout(x)
        for block in self.blocks:
            x = block(x)
        logits = self.output(self.final_norm(x))

        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), targets.reshape(-1)
            )
        return logits, loss

    @torch.inference_mode()
    def generate(
        self,
        tokens: torch.Tensor,
        *,
        max_new_tokens: int,
        temperature: float = 0.8,
        top_k: int = 40,
        stop_token: int | None = None,
    ) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            window = tokens[:, -self.config.context_length :]
            logits, _ = self(window)
            logits = logits[:, -1, :] / max(temperature, 1e-5)

            if top_k > 0:
                values, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < values[:, [-1]]] = -float("inf")

            next_token = torch.multinomial(F.softmax(logits, dim=-1), 1)
            tokens = torch.cat((tokens, next_token), dim=1)
            if stop_token is not None and torch.all(next_token == stop_token):
                break
        return tokens


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())

