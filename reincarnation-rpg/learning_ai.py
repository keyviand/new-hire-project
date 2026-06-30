"""Reinforcement-learning companion with tactical actions and exploration memory."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pygame

from entities import Actor, Enemy, Treasure
from settings import COLORS, TILE_SIZE


ACTIONS = [
    "up",
    "down",
    "left",
    "right",
    "attack",
    "heavy_attack",
    "dodge",
    "heal",
    "rest",
    "seek_treasure",
    "guard",
    "focus_boss",
    "party_guard",
    "combo_with_player",
]
DIRECTIONS = {
    "up": pygame.Vector2(0, -1),
    "down": pygame.Vector2(0, 1),
    "left": pygame.Vector2(-1, 0),
    "right": pygame.Vector2(1, 0),
}


class LearningAdventurer(Actor):
    BRAIN_VERSION = 4

    def __init__(self, x: float, y: float, brain_path: Path):
        super().__init__(
            x=x,
            y=y,
            color=COLORS["ai"],
            radius=13,
            speed=155,
            max_hp=90,
            hp=90,
            attack=11,
        )
        self.brain_path = brain_path
        self.q: dict[str, list[float]] = {}
        self.epsilon = 0.34
        self.learning_rate = 0.16
        self.discount = 0.94
        self.decision_timer = 0.0
        self.last_state: str | None = None
        self.last_action: int | None = None
        self.reward_total = 0.0
        self.episodes = 0
        self.kills = 0
        self.treasure_collected = 0
        self.potions = 2
        self.cooldown = 0.0
        self.visited: set[str] = set()
        self.lifetime_visited: set[str] = set()
        self.action_counts = {action: 0 for action in ACTIONS}
        self.stuck_anchor = pygame.Vector2(x, y)
        self.stuck_seconds = 0.0
        self.failed_moves = 0
        self.rescues = 0
        self.guard_timer = 0.0
        self.chapter2_kills = 0
        self.boss_damage = 0
        self.boss_victories = 0
        self.vault_visits = 0
        self.chapter2_tiles: set[str] = set()
        self.floor_guardian_damage = 0
        self.party_actions = 0
        self.floor_clears = 0
        self.floor1_tiles: set[str] = set()
        self.load()

    @staticmethod
    def direction_band(delta: pygame.Vector2) -> str:
        if abs(delta.x) > abs(delta.y):
            return "east" if delta.x > 0 else "west"
        return "south" if delta.y > 0 else "north"

    def state(self, world, enemies: list[Enemy], treasures: list[Treasure], party_member=None) -> str:
        active_enemies = [enemy for enemy in enemies if enemy.active]
        nearest = min(active_enemies, key=self.distance_to, default=None)
        active_treasures = [treasure for treasure in treasures if treasure.active]
        treasure = min(
            active_treasures,
            key=lambda item: self.position.distance_to(item.position),
            default=None,
        )
        hp_band = "low" if self.hp < self.max_hp * 0.32 else "mid" if self.hp < self.max_hp * 0.7 else "high"
        danger = min(
            2,
            sum(self.distance_to(enemy) < 125 for enemy in active_enemies),
        )
        blocked = "".join("1" if value else "0" for value in world.nearby_blocked(self.x, self.y))
        biome = world.biome_at_pixel(self.x, self.y)
        party_state = "solo"
        if party_member is not None:
            party_state = "near" if self.position.distance_to(party_member.position) < 140 else "far"

        if nearest is None:
            enemy_state = "none|far|none"
        else:
            delta = nearest.position - self.position
            distance = delta.length()
            distance_band = "near" if distance < 62 else "mid" if distance < 220 else "far"
            enemy_hp = "weak" if nearest.hp < nearest.max_hp * 0.4 else "strong"
            enemy_type = "boss" if nearest.boss else f"c{nearest.chapter}"
            enemy_state = f"{self.direction_band(delta)}|{distance_band}|{enemy_hp}|{enemy_type}"

        if treasure is None:
            treasure_state = "none|far"
        else:
            delta = treasure.position - self.position
            treasure_state = (
                f"{self.direction_band(delta)}|"
                f"{'near' if delta.length() < 75 else 'far'}"
            )

        return (
            f"{hp_band}|{enemy_state}|danger{danger}|"
            f"pot{int(self.potions > 0)}|loot{treasure_state}|wall{blocked}|bio{biome}|party{party_state}"
        )

    def values(self, state: str) -> list[float]:
        values = self.q.setdefault(state, [0.0] * len(ACTIONS))
        if len(values) < len(ACTIONS):
            values.extend([0.0] * (len(ACTIONS) - len(values)))
        elif len(values) > len(ACTIONS):
            del values[len(ACTIONS) :]
        return values

    def choose_action(self, state: str) -> int:
        if random.random() < self.epsilon:
            return random.randrange(len(ACTIONS))
        values = self.values(state)
        best = max(values)
        choices = [index for index, value in enumerate(values) if value == best]
        return random.choice(choices)

    def learn(
        self, state: str, action_index: int, reward: float, next_state: str
    ) -> None:
        values = self.values(state)
        target = reward + self.discount * max(self.values(next_state))
        values[action_index] += self.learning_rate * (
            target - values[action_index]
        )
        self.reward_total += reward

    def move(self, direction: pygame.Vector2, world, distance: float) -> bool:
        candidate = self.position + direction * distance
        if world.walkable_pixel(candidate.x, candidate.y):
            self.x, self.y = candidate
            self.failed_moves = 0
            return True
        self.failed_moves += 1
        return False

    def rescue(self, world, *, count_episode: bool = True) -> None:
        spawn = world.spawn_position()
        self.x, self.y = spawn
        self.hp = max(self.hp, self.max_hp // 2)
        self.potions = max(self.potions, 1)
        self.stuck_anchor = spawn.copy()
        self.stuck_seconds = 0.0
        self.failed_moves = 0
        self.visited.clear()
        self.rescues += 1
        if count_episode:
            self.episodes += 1
            self.epsilon = min(0.25, max(0.06, self.epsilon + 0.01))

    def check_stuck(self, dt: float, world, enemies: list[Enemy]) -> bool:
        if not world.walkable_pixel(self.x, self.y):
            self.rescue(world)
            return True

        moved = self.position.distance_to(self.stuck_anchor)
        nearby_enemy = any(
            enemy.active and self.distance_to(enemy) < 150 for enemy in enemies
        )
        if moved >= 70:
            self.stuck_anchor = self.position.copy()
            self.stuck_seconds = 0.0
            self.failed_moves = 0
            return False

        # Fighting, healing, and resting can legitimately keep Echo in one area.
        if nearby_enemy or self.hp < self.max_hp * 0.55:
            self.stuck_anchor = self.position.copy()
            self.stuck_seconds = 0.0
            return False

        self.stuck_seconds += dt
        if self.stuck_seconds >= 9.0 or self.failed_moves >= 14:
            self.rescue(world)
            return True
        return False

    def nearest_enemy(self, enemies: list[Enemy]) -> Enemy | None:
        return min(
            (enemy for enemy in enemies if enemy.active),
            key=self.distance_to,
            default=None,
        )

    def take_action(
        self,
        action: str,
        world,
        enemies: list[Enemy],
        treasures: list[Treasure],
        party_member=None,
    ) -> tuple[float, list[str]]:
        reward = -0.012
        events: list[str] = []
        target = self.nearest_enemy(enemies)
        self.action_counts[action] = self.action_counts.get(action, 0) + 1

        if action in DIRECTIONS:
            if self.move(DIRECTIONS[action], world, self.speed * 0.12):
                reward += 0.015
            else:
                reward -= 0.12
        elif action == "attack":
            if target and self.distance_to(target) < 62 and self.cooldown <= 0:
                target.hp -= self.attack
                self.cooldown = 0.24
                reward += 0.35
                if target.hp <= 0:
                    target.defeat()
                    self.kills += 1
                    if target.chapter == 2:
                        self.chapter2_kills += 1
                    if target.boss:
                        self.boss_victories += 1
                    reward += 5.0
                    if random.random() < 0.12:
                        self.potions = min(3, self.potions + 1)
                    events.append("Echo used a quick strike to defeat an enemy.")
            else:
                reward -= 0.08
        elif action == "heavy_attack":
            if target and self.distance_to(target) < 70 and self.cooldown <= 0:
                target.hp -= int(self.attack * 1.8)
                self.cooldown = 0.52
                reward += 0.42
                if target.hp <= 0:
                    target.defeat()
                    self.kills += 1
                    if target.chapter == 2:
                        self.chapter2_kills += 1
                    if target.boss:
                        self.boss_victories += 1
                    reward += 5.5
                    events.append("Echo learned when to use a heavy attack.")
            else:
                reward -= 0.12
        elif action == "dodge":
            if target and self.distance_to(target) < 125:
                away = self.position - target.position
                if away.length_squared() and self.move(
                    away.normalize(), world, self.speed * 0.25
                ):
                    reward += 0.28
                else:
                    reward -= 0.05
            else:
                reward -= 0.035
        elif action == "heal":
            if self.potions > 0 and self.hp < self.max_hp * 0.65:
                before = self.hp
                self.hp = min(self.max_hp, self.hp + 46)
                self.potions -= 1
                reward += 0.8 + (self.hp - before) / self.max_hp
            else:
                reward -= 0.12
        elif action == "rest":
            if self.hp < self.max_hp and (not target or self.distance_to(target) > 180):
                self.hp = min(self.max_hp, self.hp + 4)
                reward += 0.07
            else:
                reward -= 0.05
        elif action == "seek_treasure":
            treasure = min(
                (item for item in treasures if item.active),
                key=lambda item: self.position.distance_to(item.position),
                default=None,
            )
            if treasure:
                delta = treasure.position - self.position
                if delta.length_squared() and self.move(
                    delta.normalize(), world, self.speed * 0.16
                ):
                    reward += 0.04
            else:
                reward -= 0.04
        elif action == "guard":
            if target and self.distance_to(target) < 150:
                self.guard_timer = 0.45
                reward += 0.12
            else:
                reward -= 0.04
        elif action == "focus_boss":
            boss = next((enemy for enemy in enemies if enemy.active and enemy.boss), None)
            if boss:
                delta = boss.position - self.position
                if delta.length() < 72 and self.cooldown <= 0:
                    damage = int(self.attack * 1.45)
                    boss.hp -= damage
                    self.boss_damage += damage
                    self.cooldown = 0.38
                    reward += 0.65
                    if boss.hp <= 0:
                        boss.defeat()
                        self.kills += 1
                        self.chapter2_kills += 1
                        self.boss_victories += 1
                        reward += 14.0
                        events.append("Echo helped defeat the Hollow Sovereign.")
                elif delta.length_squared() and self.move(
                    delta.normalize(), world, self.speed * 0.15
                ):
                    reward += 0.08
            else:
                reward -= 0.04
        elif action == "party_guard":
            if party_member is not None:
                delta = party_member.position - self.position
                if delta.length() > 72 and delta.length_squared():
                    self.move(delta.normalize(), world, self.speed * 0.14)
                self.guard_timer = 0.6
                self.party_actions += 1
                reward += 0.16
            else:
                reward -= 0.05
        elif action == "combo_with_player":
            floor_boss = next(
                (enemy for enemy in enemies if enemy.active and enemy.floor_boss), None
            )
            if floor_boss and party_member is not None:
                delta = floor_boss.position - self.position
                if delta.length() < 76 and self.cooldown <= 0:
                    damage = int(self.attack * 1.7)
                    floor_boss.hp -= damage
                    self.floor_guardian_damage += damage
                    self.party_actions += 1
                    self.cooldown = 0.4
                    reward += 0.9
                    if floor_boss.hp <= 0:
                        floor_boss.defeat()
                        self.floor_clears += 1
                        self.boss_victories += 1
                        reward += 18.0
                        events.append("Echo completed a party combo against Asterion.")
                elif delta.length_squared() and self.move(
                    delta.normalize(), world, self.speed * 0.16
                ):
                    reward += 0.09
            else:
                reward -= 0.05

        return reward, events

    def update(
        self,
        dt: float,
        world,
        enemies: list[Enemy],
        treasures: list[Treasure] | None = None,
        party_member=None,
    ) -> list[str]:
        treasures = treasures or []
        events: list[str] = []
        self.decision_timer -= dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.guard_timer = max(0.0, self.guard_timer - dt)
        if self.check_stuck(dt, world, enemies):
            self.reward_total -= 4.0
            self.save()
            return ["Echo was stuck and returned safely to the village."]
        if self.decision_timer > 0:
            return events
        self.decision_timer = 0.12

        current_state = self.state(world, enemies, treasures, party_member)
        action_index = self.choose_action(current_state)
        reward, action_events = self.take_action(
            ACTIONS[action_index], world, enemies, treasures, party_member
        )
        events.extend(action_events)

        tile_key = f"{int(self.x // TILE_SIZE)},{int(self.y // TILE_SIZE)}"
        self.lifetime_visited.add(tile_key)
        biome = world.biome_at_pixel(self.x, self.y)
        if biome in {"ashen_reach", "vault"}:
            self.chapter2_tiles.add(tile_key)
        if biome == "floor1":
            self.floor1_tiles.add(tile_key)
        if biome == "vault":
            self.vault_visits += 1
        if tile_key not in self.visited:
            self.visited.add(tile_key)
            reward += 0.18

        for treasure in treasures:
            if treasure.active and self.position.distance_to(treasure.position) < 28:
                treasure.collect()
                self.treasure_collected += 1
                self.potions = min(3, self.potions + (1 if treasure.kind == "potion" else 0))
                reward += 3.0
                events.append("Echo discovered treasure while exploring.")

        for enemy in (enemy for enemy in enemies if enemy.active):
            distance = self.distance_to(enemy)
            if distance < self.radius + enemy.radius + 5:
                damage = max(1, enemy.attack // 3)
                if self.guard_timer > 0:
                    damage = max(1, damage // 2)
                self.hp -= damage
                reward -= 0.18 + damage / self.max_hp
            elif enemy.role == "skirmisher" and distance < enemy.attack_range:
                self.hp -= 1
                reward -= 0.08

        if self.hp <= 0:
            self.rescue(world)
            self.hp = self.max_hp
            self.potions = 2
            reward -= 6.0
            self.epsilon = max(0.06, self.epsilon * 0.992)
            self.save()
            events.append(f"Echo began tactical episode {self.episodes + 1}.")

        next_state = self.state(world, enemies, treasures, party_member)
        self.learn(current_state, action_index, reward, next_state)
        self.last_state = current_state
        self.last_action = action_index
        return events

    def mastery_breakdown(self, world) -> dict[str, float]:
        """Return curriculum progress used to decide when the game needs more depth."""
        exploration = min(
            1.0,
            len(self.lifetime_visited) / max(1, world.walkable_tile_count * 0.65),
        )
        knowledge = min(1.0, len(self.q) / 8000)
        tactics = sum(
            min(1.0, self.action_counts.get(action, 0) / 250)
            for action in ACTIONS
        ) / len(ACTIONS)
        combat = min(1.0, self.kills / 2500)
        treasure = min(1.0, self.treasure_collected / 300)
        overall = (
            exploration * 0.30
            + knowledge * 0.25
            + tactics * 0.20
            + combat * 0.15
            + treasure * 0.10
        )
        return {
            "overall": overall,
            "exploration": exploration,
            "knowledge": knowledge,
            "tactics": tactics,
            "combat": combat,
            "treasure": treasure,
        }

    def chapter2_mastery(self) -> dict[str, float]:
        exploration = min(1.0, len(self.chapter2_tiles) / 300)
        new_tactics = (
            min(1.0, self.action_counts.get("guard", 0) / 300)
            + min(1.0, self.action_counts.get("focus_boss", 0) / 300)
        ) / 2
        enemies = min(1.0, self.chapter2_kills / 350)
        boss_skill = min(1.0, self.boss_damage / 12000)
        boss_wins = min(1.0, self.boss_victories / 8)
        overall = (
            exploration * 0.25
            + new_tactics * 0.20
            + enemies * 0.20
            + boss_skill * 0.20
            + boss_wins * 0.15
        )
        return {
            "overall": overall,
            "reach_exploration": exploration,
            "new_tactics": new_tactics,
            "chapter2_combat": enemies,
            "boss_skill": boss_skill,
            "boss_victories": boss_wins,
        }

    def vrmmo_mastery(self) -> dict[str, float]:
        exploration = min(1.0, len(self.floor1_tiles) / 220)
        party = min(1.0, self.party_actions / 1200)
        guardian_skill = min(1.0, self.floor_guardian_damage / 18000)
        clears = min(1.0, self.floor_clears / 8)
        new_actions = (
            min(1.0, self.action_counts.get("party_guard", 0) / 300)
            + min(1.0, self.action_counts.get("combo_with_player", 0) / 300)
        ) / 2
        overall = (
            exploration * 0.25
            + party * 0.20
            + guardian_skill * 0.20
            + clears * 0.20
            + new_actions * 0.15
        )
        return {
            "overall": overall,
            "floor_exploration": exploration,
            "party_coordination": party,
            "guardian_skill": guardian_skill,
            "floor_clears": clears,
            "new_actions": new_actions,
        }

    def readiness_message(self, world) -> str:
        percent = self.mastery_breakdown(world)["overall"] * 100
        if percent >= 85:
            return "Echo has mastered this chapter. Add new content."
        if percent >= 70:
            return "Echo is close to mastery. Plan the next chapter."
        if percent >= 45:
            return "Echo is learning steadily. More training is useful."
        return "Echo is still exploring the current systems."

    def save(self) -> None:
        payload = {
            "version": self.BRAIN_VERSION,
            "q": self.q,
            "epsilon": self.epsilon,
            "episodes": self.episodes,
            "kills": self.kills,
            "treasure_collected": self.treasure_collected,
            "rescues": self.rescues,
            "lifetime_visited": sorted(self.lifetime_visited),
            "action_counts": self.action_counts,
            "chapter2_kills": self.chapter2_kills,
            "boss_damage": self.boss_damage,
            "boss_victories": self.boss_victories,
            "vault_visits": self.vault_visits,
            "chapter2_tiles": sorted(self.chapter2_tiles),
            "floor_guardian_damage": self.floor_guardian_damage,
            "party_actions": self.party_actions,
            "floor_clears": self.floor_clears,
            "floor1_tiles": sorted(self.floor1_tiles),
            "reward_total": self.reward_total,
        }
        self.brain_path.write_text(json.dumps(payload), encoding="utf-8")

    def load(self) -> None:
        if not self.brain_path.exists():
            return
        try:
            payload = json.loads(self.brain_path.read_text(encoding="utf-8"))
            self.episodes = int(payload.get("episodes", 0))
            self.kills = int(payload.get("kills", 0))
            self.treasure_collected = int(payload.get("treasure_collected", 0))
            self.rescues = int(payload.get("rescues", 0))
            self.lifetime_visited = set(payload.get("lifetime_visited", []))
            saved_counts = payload.get("action_counts", {})
            self.action_counts = {
                action: int(saved_counts.get(action, 0)) for action in ACTIONS
            }
            self.chapter2_kills = int(payload.get("chapter2_kills", 0))
            self.boss_damage = int(payload.get("boss_damage", 0))
            self.boss_victories = int(payload.get("boss_victories", 0))
            self.vault_visits = int(payload.get("vault_visits", 0))
            self.chapter2_tiles = set(payload.get("chapter2_tiles", []))
            self.floor_guardian_damage = int(payload.get("floor_guardian_damage", 0))
            self.party_actions = int(payload.get("party_actions", 0))
            self.floor_clears = int(payload.get("floor_clears", 0))
            self.floor1_tiles = set(payload.get("floor1_tiles", []))
            self.reward_total = float(payload.get("reward_total", 0))
            if int(payload.get("version", 1)) == self.BRAIN_VERSION:
                self.q = payload.get("q", {})
                self.epsilon = float(payload.get("epsilon", self.epsilon))
            else:
                # Keep lifetime accomplishments, but reset incompatible old states.
                self.q = {}
                self.epsilon = 0.34
        except (OSError, ValueError, TypeError):
            self.q = {}
