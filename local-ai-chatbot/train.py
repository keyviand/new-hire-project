"""Train the local chatbot from random weights on a local text file."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import torch

from model import LocalChatbot, ModelConfig, parameter_count
from tokenizer import ByteTokenizer


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data" / "training.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "checkpoints")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--accumulation-steps", type=int, default=4)
    parser.add_argument("--context-length", type=int, default=512)
    parser.add_argument("--d-model", type=int, default=384)
    parser.add_argument("--heads", type=int, default=6)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--save-every", type=int, default=500)
    parser.add_argument("--seed", type=int, default=1337)
    return parser.parse_args()


def get_batch(
    tokens: torch.Tensor,
    batch_size: int,
    context_length: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor]:
    maximum = len(tokens) - context_length - 1
    starts = torch.randint(0, maximum, (batch_size,))
    inputs = torch.stack([tokens[i : i + context_length] for i in starts])
    targets = torch.stack([tokens[i + 1 : i + context_length + 1] for i in starts])
    return inputs.to(device), targets.to(device)


def save_checkpoint(
    model: LocalChatbot,
    optimizer: torch.optim.Optimizer,
    step: int,
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "step": step,
        "config": model.config.to_dict(),
    }
    torch.save(payload, output / "latest.pt")
    (output / "config.json").write_text(
        json.dumps(model.config.to_dict(), indent=2), encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)

    if not args.data.exists():
        raise FileNotFoundError(f"Training data not found: {args.data}")

    tokenizer = ByteTokenizer()
    text = args.data.read_text(encoding="utf-8")
    encoded = tokenizer.encode(text, add_bos=True, add_eos=True)
    if len(encoded) <= args.context_length + 1:
        raise ValueError(
            f"Training file has only {len(encoded):,} tokens. Add more text or use "
            f"--context-length {max(32, len(encoded) // 2)}."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    config = ModelConfig(
        vocab_size=tokenizer.vocab_size,
        context_length=args.context_length,
        d_model=args.d_model,
        n_heads=args.heads,
        n_layers=args.layers,
    )
    model = LocalChatbot(config).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=args.learning_rate, betas=(0.9, 0.95), weight_decay=0.1
    )
    data = torch.tensor(encoded, dtype=torch.long)
    use_amp = device.type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    print(f"Device: {device}")
    if use_amp:
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Parameters: {parameter_count(model):,}")
    print(f"Training tokens: {len(data):,}")
    print(f"Steps: {args.steps:,}")

    model.train()
    optimizer.zero_grad(set_to_none=True)
    started = time.time()

    for step in range(1, args.steps + 1):
        total_loss = 0.0
        for _ in range(args.accumulation_steps):
            inputs, targets = get_batch(
                data, args.batch_size, args.context_length, device
            )
            with torch.autocast(
                device_type=device.type, dtype=torch.float16, enabled=use_amp
            ):
                _, loss = model(inputs, targets)
                scaled_loss = loss / args.accumulation_steps
            scaler.scale(scaled_loss).backward()
            total_loss += loss.item()

        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        optimizer.zero_grad(set_to_none=True)

        if step == 1 or step % 25 == 0:
            elapsed = time.time() - started
            average_loss = total_loss / args.accumulation_steps
            perplexity = math.exp(min(average_loss, 20))
            print(
                f"step {step:>6} | loss {average_loss:.4f} | "
                f"perplexity {perplexity:.2f} | {elapsed:.1f}s"
            )

        if step % args.save_every == 0 or step == args.steps:
            save_checkpoint(model, optimizer, step, args.output)
            print(f"Saved checkpoint at step {step}: {args.output / 'latest.pt'}")


if __name__ == "__main__":
    main()

