"""Background TCP client used by the optional online co-op mode."""

from __future__ import annotations

import json
import socket
import threading
import time


class CoopClient:
    def __init__(self, host: str, port: int, name: str):
        self.host = host
        self.port = port
        self.name = name
        self.player_id: str | None = None
        self.connected = False
        self.error: str | None = None
        self.snapshot: dict = {"players": [], "guardian": {}}
        self._state: dict | None = None
        self._attacks: list[int] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def set_state(self, **state) -> None:
        with self._lock:
            self._state = {"type": "state", **state}

    def attack_guardian(self, damage: int) -> None:
        with self._lock:
            self._attacks.append(int(damage))

    def get_snapshot(self) -> dict:
        with self._lock:
            return {
                "players": [dict(player) for player in self.snapshot.get("players", [])],
                "guardian": dict(self.snapshot.get("guardian", {})),
            }

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=1.5)

    @staticmethod
    def _send(file, payload: dict) -> None:
        file.write(json.dumps(payload, separators=(",", ":")).encode() + b"\n")
        file.flush()

    @staticmethod
    def _read(file) -> dict:
        raw = file.readline(65536)
        if not raw:
            raise ConnectionError("Server closed the connection")
        return json.loads(raw)

    def _run(self) -> None:
        try:
            with socket.create_connection((self.host, self.port), timeout=5) as sock:
                sock.settimeout(3)
                with sock.makefile("rwb", buffering=0) as file:
                    self._send(file, {"type": "join", "name": self.name})
                    welcome = self._read(file)
                    if welcome.get("type") == "error":
                        raise ConnectionError(welcome.get("message", "Server rejected join"))
                    self.player_id = welcome["player_id"]
                    with self._lock:
                        self.snapshot = welcome.get("snapshot", self.snapshot)
                    self.connected = True
                    while not self._stop.is_set():
                        with self._lock:
                            attacks = self._attacks[:]
                            self._attacks.clear()
                            state = dict(self._state) if self._state else {"type": "ping"}
                        for damage in attacks:
                            self._send(file, {"type": "attack_guardian", "damage": damage})
                            response = self._read(file)
                            with self._lock:
                                self.snapshot = response
                        self._send(file, state)
                        response = self._read(file)
                        with self._lock:
                            self.snapshot = response
                        time.sleep(0.08)
        except (OSError, ConnectionError, ValueError, json.JSONDecodeError) as error:
            self.error = str(error)
        finally:
            self.connected = False

