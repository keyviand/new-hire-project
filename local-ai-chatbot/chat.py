"""Chat with a locally trained checkpoint."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from model import LocalChatbot, ModelConfig
from tokenizer import ByteTokenizer


ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint", type=Path, default=ROOT / "checkpoints" / "latest.pt"
    )
    parser.add_argument("--name", default="Nova")
    parser.add_argument("--max-new-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.75)
    parser.add_argument("--top-k", type=int, default=40)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.checkpoint.exists():
        raise FileNotFoundError(
            f"No trained model found at {args.checkpoint}. Run train.py first."
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    config = ModelConfig(**checkpoint["config"])
    model = LocalChatbot(config).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    tokenizer = ByteTokenizer()

    history = (
        f"System: You are {args.name}, a friendly and useful local AI assistant.\n"
    )
    print(f"\n{args.name} is running locally on {device}.")
    print("Type /reset to clear memory or /quit to stop.\n")

    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_text:
            continue
        if user_text.lower() == "/quit":
            print("Goodbye.")
            break
        if user_text.lower() == "/reset":
            history = (
                f"System: You are {args.name}, a friendly and useful local AI assistant.\n"
            )
            print("Conversation cleared.\n")
            continue

        prompt = history + f"User: {user_text}\nAssistant:"
        prompt_tokens = tokenizer.encode(prompt, add_bos=True)
        prompt_tokens = prompt_tokens[-config.context_length :]
        input_tensor = torch.tensor([prompt_tokens], dtype=torch.long, device=device)
        generated = model.generate(
            input_tensor,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            top_k=args.top_k,
        )
        new_tokens = generated[0, len(prompt_tokens) :].tolist()
        answer = tokenizer.decode(new_tokens)
        answer = answer.split("\nUser:", 1)[0].split("\nSystem:", 1)[0].strip()
        if not answer:
            answer = "(The model did not produce a readable answer.)"

        print(f"{args.name}: {answer}\n")
        history += f"User: {user_text}\nAssistant: {answer}\n"
        history_tokens = tokenizer.encode(history)
        if len(history_tokens) > config.context_length - 100:
            history = tokenizer.decode(
                history_tokens[-(config.context_length - 100) :]
            )


if __name__ == "__main__":
    main()

