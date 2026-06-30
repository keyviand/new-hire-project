"""Fast offline checks for tokenizer and Transformer tensor shapes."""

import torch

from model import LocalChatbot, ModelConfig
from tokenizer import ByteTokenizer


def main() -> None:
    tokenizer = ByteTokenizer()
    sample = "Hello, local AI! 🤖"
    assert tokenizer.decode(tokenizer.encode(sample)) == sample

    config = ModelConfig(
        context_length=32, d_model=48, n_heads=4, n_layers=2, dropout=0.0
    )
    model = LocalChatbot(config)
    inputs = torch.randint(0, config.vocab_size, (2, 16))
    logits, loss = model(inputs, inputs)
    assert logits.shape == (2, 16, config.vocab_size)
    assert loss is not None and torch.isfinite(loss)

    generated = model.generate(inputs[:1, :4], max_new_tokens=3, top_k=10)
    assert generated.shape == (1, 7)
    print("All model and tokenizer checks passed.")


if __name__ == "__main__":
    main()

