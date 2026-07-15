"""Authoritative LAN co-op server for Everdawn Online: Ascension."""

from __future__ import annotations

import argparse
import json
import math
import socketserver
import threading
import time
import uuid

from settings import TILE_SIZE, WORLD_HEIGHT, WORLD_WIDTH


GUARDIAN_POSITION = ((34 + 0.5) * TILE_SIZE, (12 + 0.5) * TILE_SIZE)
SPAWN_POSITION = ((8 + 0.5) * TILE_SIZE, (8 + 0.5) * TILE_SIZE)
PLAYER_COLORS = [
    [116, 214, 255],
    [255, 166, 92],
    [116, 235, 155],
    [236, 118, 226],
]


class CoopState:
    def __init__(self, max_players: int = 4):
        self.max_players = max_players
        self.players: dict[str, dict] = {}
        self.guardian_hp = 850
        self.guardian_max_hp = 850
        self.floor_cleared = False
        self.lock = threading.RLock()

    def join(self, name: str) -> dict:
        with self.lock:
            if len(self.players) >= self.max_players:
                raise ValueError("Server is full")
            player_id = uuid.uuid4().hex[:10]
            color = PLAYER_COLORS[len(self.players) % len(PLAYER_COLORS)]
            self.players[player_id] = {
                "id": player_id,
                "name": str(name)[:18] or "Adventurer",
                "x": SPAWN_POSITION[0],
                "y": SPAWN_POSITION[1],
                "hp": 100,
                "max_hp": 100,
                "level": 1,
                "color": color,
                "last_update": time.monotonic(),
                "last_attack": 0.0,
            }
            return {"type": "welcome", "player_id": player_id, "snapshot": self.snapshot()}

    def leave(self, player_id: str) -> None:
        with self.lock:
            self.players.pop(player_id, None)

    def update_player(self, player_id: str, message: dict) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            now = time.monotonic()
            elapsed = max(0.02, min(0.5, now - player["last_update"]))
            requested_x = float(message.get("x", player["x"]))
            requested_y = float(message.get("y", player["y"]))
            requested_x = max(0, min(WORLD_WIDTH * TILE_SIZE, requested_x))
            requested_y = max(0, min(WORLD_HEIGHT * TILE_SIZE, requested_y))
            distance = math.dist((player["x"], player["y"]), (requested_x, requested_y))
            maximum = 260 * elapsed + 42
            if distance <= maximum:
                player["x"], player["y"] = requested_x, requested_y
            player["hp"] = max(0, min(int(message.get("hp", player["hp"])), int(message.get("max_hp", 100))))
            player["max_hp"] = max(1, min(int(message.get("max_hp", 100)), 10000))
            player["level"] = max(1, min(int(message.get("level", 1)), 999))
            player["last_update"] = now

    def attack_guardian(self, player_id: str, message: dict) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player or self.floor_cleared:
                return
            now = time.monotonic()
            if now - player["last_attack"] < 0.18:
                return
            if math.dist((player["x"], player["y"]), GUARDIAN_POSITION) > 190:
                return
            damage = max(1, min(int(message.get("damage", 1)), 120))
            self.guardian_hp = max(0, self.guardian_hp - damage)
            self.floor_cleared = self.guardian_hp == 0
            player["last_attack"] = now

    def snapshot(self) -> dict:
        with self.lock:
            now = time.monotonic()
            stale = [
                player_id
                for player_id, player in self.players.items()
                if now - player["last_update"] > 15
            ]
            for player_id in stale:
                self.players.pop(player_id, None)
            return {
                "type": "snapshot",
                "players": list(self.players.values()),
                "guardian": {
                    "hp": self.guardian_hp,
                    "max_hp": self.guardian_max_hp,
                    "cleared": self.floor_cleared,
                },
            }


STATE = CoopState()


class CoopHandler(socketserver.StreamRequestHandler):
    player_id: str | None = None

    def send(self, payload: dict) -> None:
        self.wfile.write(json.dumps(payload, separators=(",", ":")).encode() + b"\n")
        self.wfile.flush()

    def handle(self) -> None:
        try:
            first = json.loads(self.rfile.readline(65536))
            if first.get("type") != "join":
                self.send({"type": "error", "message": "Join required"})
                return
            welcome = STATE.join(first.get("name", "Adventurer"))
            self.player_id = welcome["player_id"]
            self.send(welcome)
            while True:
                raw = self.rfile.readline(65536)
                if not raw:
                    break
                message = json.loads(raw)
                kind = message.get("type")
                if kind == "state":
                    STATE.update_player(self.player_id, message)
                elif kind == "attack_guardian":
                    STATE.attack_guardian(self.player_id, message)
                elif kind == "ping":
                    pass
                self.send(STATE.snapshot())
        except (ConnectionError, OSError, ValueError, json.JSONDecodeError) as error:
            if self.player_id is None:
                try:
                    self.send({"type": "error", "message": str(error)})
                except OSError:
                    pass
        finally:
            if self.player_id:
                STATE.leave(self.player_id)


class ThreadingCoopServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    global STATE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--max-players", type=int, default=4)
    args = parser.parse_args()
    STATE = CoopState(args.max_players)
    with ThreadingCoopServer((args.host, args.port), CoopHandler) as server:
        print(f"Everdawn co-op server listening on {args.host}:{args.port}")
        print(f"Maximum players: {args.max_players}. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    main()

