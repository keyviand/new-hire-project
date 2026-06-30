"""Local-only web interface for Nova. No API or internet connection is used."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import torch

from model import LocalChatbot, ModelConfig
from tokenizer import ByteTokenizer


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"


class NovaEngine:
    def __init__(self, checkpoint_path: Path, name: str):
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"No trained model found at {checkpoint_path}. Run train.py first."
            )

        self.name = name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint = torch.load(
            checkpoint_path, map_location=self.device, weights_only=False
        )
        self.step = int(checkpoint.get("step", 0))
        self.config = ModelConfig(**checkpoint["config"])
        self.model = LocalChatbot(self.config).to(self.device)
        self.model.load_state_dict(checkpoint["model"])
        self.model.eval()
        self.tokenizer = ByteTokenizer()

    def reply(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_new_tokens: int = 220,
    ) -> str:
        lines = [
            f"System: You are {self.name}, a friendly and useful local AI assistant."
        ]
        for message in messages[-12:]:
            role = message.get("role")
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                lines.append(f"User: {content}")
            elif role == "assistant":
                lines.append(f"Assistant: {content}")
        lines.append("Assistant:")
        prompt = "\n".join(lines)

        prompt_tokens = self.tokenizer.encode(prompt, add_bos=True)
        prompt_tokens = prompt_tokens[-self.config.context_length :]
        input_tensor = torch.tensor(
            [prompt_tokens], dtype=torch.long, device=self.device
        )
        generated = self.model.generate(
            input_tensor,
            max_new_tokens=max_new_tokens,
            temperature=max(0.1, min(1.5, temperature)),
            top_k=40,
        )
        new_tokens = generated[0, len(prompt_tokens) :].tolist()
        answer = self.tokenizer.decode(new_tokens)
        for marker in ("\nUser:", "\nSystem:", "\nAssistant:"):
            answer = answer.split(marker, 1)[0]
        return answer.strip() or "(Nova did not produce a readable answer.)"


def make_handler(engine: NovaEngine):
    class NovaHandler(BaseHTTPRequestHandler):
        server_version = "NovaLocal/1.0"

        def send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/status":
                self.send_json(
                    200,
                    {
                        "name": engine.name,
                        "device": str(engine.device),
                        "gpu": (
                            torch.cuda.get_device_name(0)
                            if engine.device.type == "cuda"
                            else None
                        ),
                        "trainingStep": engine.step,
                        "contextLength": engine.config.context_length,
                    },
                )
                return

            relative = "index.html" if path == "/" else path.lstrip("/")
            requested = (WEB_ROOT / relative).resolve()
            if WEB_ROOT.resolve() not in requested.parents and requested != WEB_ROOT:
                self.send_error(403)
                return
            if not requested.is_file():
                self.send_error(404)
                return

            content = requested.read_bytes()
            content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self) -> None:
            if urlparse(self.path).path != "/api/chat":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 100_000:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(length))
                messages = payload.get("messages", [])
                if not isinstance(messages, list) or not messages:
                    raise ValueError("A message is required")
                answer = engine.reply(
                    messages,
                    temperature=float(payload.get("temperature", 0.7)),
                )
                self.send_json(200, {"reply": answer})
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            except Exception as error:
                print(f"Generation error: {error}")
                self.send_json(500, {"error": "Nova could not generate a response."})

        def log_message(self, format: str, *args) -> None:
            print(f"{self.client_address[0]} - {format % args}")

    return NovaHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint", type=Path, default=ROOT / "checkpoints" / "latest.pt"
    )
    parser.add_argument("--name", default="Nova")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"Loading {args.name} from {args.checkpoint}...")
    engine = NovaEngine(args.checkpoint, args.name)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(engine))
    print(f"{args.name} is ready on http://{args.host}:{args.port}")
    print(f"Device: {engine.device} | training step: {engine.step}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Nova.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

