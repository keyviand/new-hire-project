"""Small, inspectable tabular Q-learning brain for Echo."""

from __future__ import annotations

import json
import random
from pathlib import Path


class EchoQLearner:
    """Learn action values for discrete game states using Q-learning."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        learning_rate: float = 0.18,
        discount: float = 0.92,
        epsilon: float = 0.28,
        minimum_epsilon: float = 0.05,
        epsilon_decay: float = 0.9995,
        seed: int | None = None,
    ) -> None:
        self.path = path
        self.learning_rate = learning_rate
        self.discount = discount
        self.epsilon = epsilon
        self.minimum_epsilon = minimum_epsilon
        self.epsilon_decay = epsilon_decay
        self.random = random.Random(seed)
        self.q_table: dict[str, dict[str, float]] = {}
        self.decisions = 0
        self.updates = 0
        self.explorations = 0
        self.total_reward = 0.0
        self.action_counts: dict[str, int] = {}
        self.last_state = "waiting"
        self.last_action = "patrol"
        self.last_reward = 0.0
        self.last_q_change = 0.0
        self._load()

    def _row(self, state: str, actions: list[str]) -> dict[str, float]:
        row = self.q_table.setdefault(state, {})
        for action in actions:
            row.setdefault(action, 0.0)
        return row

    def choose_action(self, state: str, valid_actions: list[str]) -> str:
        if not valid_actions:
            raise ValueError("Echo needs at least one valid action")
        row = self._row(state, valid_actions)
        self.decisions += 1
        if self.random.random() < self.epsilon:
            action = self.random.choice(valid_actions)
            self.explorations += 1
        else:
            best = max(row[action] for action in valid_actions)
            choices = [action for action in valid_actions if row[action] == best]
            action = self.random.choice(choices)
        self.epsilon = max(self.minimum_epsilon, self.epsilon * self.epsilon_decay)
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        self.last_state = state
        self.last_action = action
        return action

    def learn(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        next_actions: list[str],
        *,
        terminal: bool = False,
    ) -> float:
        row = self._row(state, [action])
        old_value = row[action]
        future_value = 0.0
        if not terminal and next_actions:
            next_row = self._row(next_state, next_actions)
            future_value = max(next_row[action_name] for action_name in next_actions)
        target = reward + self.discount * future_value
        new_value = old_value + self.learning_rate * (target - old_value)
        row[action] = new_value
        self.updates += 1
        self.total_reward += reward
        self.last_reward = reward
        self.last_q_change = new_value - old_value
        return new_value

    def snapshot(self, state: str | None = None) -> dict:
        inspected_state = state or self.last_state
        values = self.q_table.get(inspected_state, {})
        return {
            "algorithm": "Tabular Q-learning",
            "state": inspected_state,
            "action": self.last_action,
            "last_reward": round(self.last_reward, 3),
            "last_q_change": round(self.last_q_change, 4),
            "total_reward": round(self.total_reward, 2),
            "epsilon": round(self.epsilon, 4),
            "learning_rate": self.learning_rate,
            "discount": self.discount,
            "decisions": self.decisions,
            "updates": self.updates,
            "explorations": self.explorations,
            "states_learned": len(self.q_table),
            "q_values": {key: round(value, 3) for key, value in sorted(values.items())},
            "action_counts": dict(sorted(self.action_counts.items())),
        }

    def save(self) -> None:
        if not self.path:
            return
        payload = {
            "q_table": self.q_table,
            "epsilon": self.epsilon,
            "decisions": self.decisions,
            "updates": self.updates,
            "explorations": self.explorations,
            "total_reward": self.total_reward,
            "action_counts": self.action_counts,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def _load(self) -> None:
        if not self.path or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.q_table = payload.get("q_table", {})
            self.epsilon = max(self.minimum_epsilon, float(payload.get("epsilon", self.epsilon)))
            self.decisions = int(payload.get("decisions", 0))
            self.updates = int(payload.get("updates", 0))
            self.explorations = int(payload.get("explorations", 0))
            self.total_reward = float(payload.get("total_reward", 0.0))
            self.action_counts = {str(key): int(value) for key, value in payload.get("action_counts", {}).items()}
        except (OSError, ValueError, TypeError):
            self.q_table = {}
