from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

import pygame

from settings import TILE_SIZE, COLORS


@dataclass
class Actor:
    x: float
    y: float
    color: tuple[int, int, int]
    radius: int = 15
    speed: float = 180.0
    max_hp: int = 100
    hp: int = 100
    attack: int = 12

    @property
    def position(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, self.y)

    def distance_to(self, other: "Actor") -> float:
        return self.position.distance_to(other.position)

    def draw(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        pos = self.position - camera
        shadow = pygame.Rect(0, 0, self.radius * 2, 9)
        shadow.center = (round(pos.x), round(pos.y + self.radius))
        pygame.draw.ellipse(surface, (10, 14, 20, 90), shadow)
        pygame.draw.circle(surface, self.color, pos, self.radius)
        pygame.draw.circle(surface, (245, 249, 255), pos, self.radius, 2)
        if self.hp < self.max_hp:
            width = 36
            bar = pygame.Rect(pos.x - width / 2, pos.y - 26, width, 5)
            pygame.draw.rect(surface, (45, 24, 31), bar, border_radius=3)
            fill = bar.copy()
            fill.width = max(0, width * self.hp / self.max_hp)
            pygame.draw.rect(surface, COLORS["health"], fill, border_radius=3)


@dataclass
class Hero(Actor):
    name: str = "Ari"
    level: int = 1
    xp: int = 0
    xp_next: int = 60
    mana: int = 40
    max_mana: int = 40
    gold: int = 0
    potions: int = 2
    soul_shards: int = 0
    rebirths: int = 0
    legacy_power: int = 0
    kills: int = 0
    quest_kills: int = 0
    quest_target: int = 5
    attack_cooldown: float = 0.0
    hurt_cooldown: float = 0.0
    dodge_cooldown: float = 0.0
    spell_cooldown: float = 0.0
    weapon_level: int = 0
    armor_level: int = 0
    void_cores: int = 0
    boss_kills: int = 0
    current_floor: int = 1
    floors_cleared: int = 0
    sword_mastery: int = 0
    combo: int = 0
    combo_timer: float = 0.0
    parry_window: float = 0.0
    skill_cooldown: float = 0.0
    color: tuple[int, int, int] = COLORS["player"]

    def update_timers(self, dt: float) -> None:
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.hurt_cooldown = max(0.0, self.hurt_cooldown - dt)
        self.dodge_cooldown = max(0.0, self.dodge_cooldown - dt)
        self.spell_cooldown = max(0.0, self.spell_cooldown - dt)
        self.mana = min(self.max_mana, self.mana + 4 * dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        self.parry_window = max(0.0, self.parry_window - dt)
        self.skill_cooldown = max(0.0, self.skill_cooldown - dt)
        if self.combo_timer <= 0:
            self.combo = 0

    def gain_xp(self, amount: int) -> list[str]:
        events = []
        self.xp += amount
        while self.xp >= self.xp_next:
            self.xp -= self.xp_next
            self.level += 1
            self.xp_next = int(self.xp_next * 1.42)
            self.max_hp += 16
            self.hp = self.max_hp
            self.max_mana += 7
            self.mana = self.max_mana
            self.attack += 3
            events.append(f"Level up! You reached level {self.level}.")
        return events

    def use_potion(self) -> str:
        if self.potions <= 0:
            return "You have no healing potions."
        if self.hp >= self.max_hp:
            return "Your health is already full."
        self.potions -= 1
        healed = min(55, self.max_hp - self.hp)
        self.hp += healed
        return f"You recovered {healed} health."

    def reincarnate(self, spawn: pygame.Vector2) -> str:
        if self.level < 5:
            return "Reach level 5 before reincarnating."
        gained = max(1, self.level // 3) + self.soul_shards
        self.rebirths += 1
        self.legacy_power += gained
        self.level = 1
        self.xp = 0
        self.xp_next = 60
        self.max_hp = 100 + self.legacy_power * 5
        self.hp = self.max_hp
        self.max_mana = 40 + self.legacy_power * 2
        self.mana = self.max_mana
        self.attack = 12 + self.legacy_power * 2
        self.soul_shards = 0
        self.x, self.y = spawn
        return f"Reborn with {gained} new legacy power. Total legacy: {self.legacy_power}."

    @property
    def damage_reduction(self) -> float:
        return min(0.45, self.armor_level * 0.08)

    def upgrade_equipment(self) -> str:
        cost = 2 + self.weapon_level + self.armor_level
        if self.void_cores < cost:
            return f"The forge needs {cost} void cores."
        self.void_cores -= cost
        if self.weapon_level <= self.armor_level:
            self.weapon_level += 1
            self.attack += 4
            return f"Voidblade upgraded to rank {self.weapon_level}."
        self.armor_level += 1
        self.max_hp += 12
        self.hp = self.max_hp
        return f"Night armor upgraded to rank {self.armor_level}."


@dataclass
class Enemy(Actor):
    kind: str = "Slime"
    xp_reward: int = 12
    gold_reward: int = 4
    active: bool = True
    respawn_timer: float = 0.0
    wander_angle: float = field(default_factory=lambda: random.random() * math.tau)
    think_timer: float = 0.0
    role: str = "chaser"
    attack_range: float = 32.0
    attack_cooldown: float = 0.0
    chapter: int = 1
    boss: bool = False
    phase: int = 1
    floor_boss: bool = False

    def update(self, dt: float, target: Actor, world) -> None:
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True
                self.hp = self.max_hp
            return

        self.think_timer -= dt
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        delta = target.position - self.position
        distance = delta.length()
        if distance < 260:
            direction = delta.normalize() if delta.length_squared() else pygame.Vector2()
            if self.role == "skirmisher" and distance < 105:
                direction *= -1
            elif self.role == "guardian" and distance > 150:
                direction *= 0.55
            velocity = direction * self.speed
        else:
            if self.think_timer <= 0:
                self.wander_angle += random.uniform(-1.4, 1.4)
                self.think_timer = random.uniform(0.7, 2.0)
            velocity = pygame.Vector2(
                math.cos(self.wander_angle), math.sin(self.wander_angle)
            ) * self.speed * 0.32

        candidate = self.position + velocity * dt
        if world.walkable_pixel(candidate.x, candidate.y):
            self.x, self.y = candidate
        else:
            self.wander_angle += math.pi * 0.7

    def defeat(self) -> None:
        self.active = False
        self.respawn_timer = 30 if self.boss else random.uniform(7, 13)


def make_enemy(tile_x: int, tile_y: int, difficulty: int = 1) -> Enemy:
    elite = difficulty >= 3
    hp = 28 + difficulty * 15
    role = "guardian" if elite else random.choice(["chaser", "chaser", "skirmisher"])
    return Enemy(
        x=tile_x * TILE_SIZE + TILE_SIZE / 2,
        y=tile_y * TILE_SIZE + TILE_SIZE / 2,
        color=COLORS["elite"] if elite else COLORS["enemy"],
        radius=18 if elite else 14,
        speed=78 + difficulty * 5,
        max_hp=hp,
        hp=hp,
        attack=5 + difficulty * 3,
        kind=(
            "Ash Warden"
            if elite
            else "Wisp"
            if role == "skirmisher"
            else random.choice(["Slime", "Fangling"])
        ),
        xp_reward=10 + difficulty * 8,
        gold_reward=3 + difficulty * 3,
        role=role,
        attack_range=110 if role == "skirmisher" else 34,
    )


def make_chapter2_enemy(tile_x: int, tile_y: int, kind: str | None = None) -> Enemy:
    kind = kind or random.choice(["Void Stalker", "Cinder Mage", "Hollow Knight"])
    role = "skirmisher" if kind == "Cinder Mage" else "guardian" if kind == "Hollow Knight" else "chaser"
    hp = 115 if role == "guardian" else 82
    return Enemy(
        x=tile_x * TILE_SIZE + TILE_SIZE / 2,
        y=tile_y * TILE_SIZE + TILE_SIZE / 2,
        color=(204, 77, 220) if role != "guardian" else (134, 116, 154),
        radius=18 if role == "guardian" else 15,
        speed=96 if role == "chaser" else 75,
        max_hp=hp,
        hp=hp,
        attack=15 if role != "guardian" else 19,
        kind=kind,
        xp_reward=45,
        gold_reward=15,
        role=role,
        attack_range=145 if role == "skirmisher" else 38,
        chapter=2,
    )


def make_boss(tile_x: int, tile_y: int) -> Enemy:
    return Enemy(
        x=tile_x * TILE_SIZE + TILE_SIZE / 2,
        y=tile_y * TILE_SIZE + TILE_SIZE / 2,
        color=(255, 72, 166),
        radius=28,
        speed=82,
        max_hp=650,
        hp=650,
        attack=24,
        kind="The Hollow Sovereign",
        xp_reward=350,
        gold_reward=180,
        role="guardian",
        attack_range=95,
        chapter=2,
        boss=True,
    )


def make_floor_guardian(tile_x: int, tile_y: int) -> Enemy:
    return Enemy(
        x=tile_x * TILE_SIZE + TILE_SIZE / 2,
        y=tile_y * TILE_SIZE + TILE_SIZE / 2,
        color=(70, 224, 235),
        radius=30,
        speed=105,
        max_hp=850,
        hp=850,
        attack=27,
        kind="Asterion, Skyglass Sentinel",
        xp_reward=500,
        gold_reward=250,
        role="guardian",
        attack_range=105,
        chapter=3,
        boss=True,
        floor_boss=True,
    )


@dataclass
class Treasure:
    x: float
    y: float
    kind: str = "chest"
    value: int = 15
    active: bool = True
    respawn_timer: float = 0.0

    @property
    def position(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, self.y)

    def collect(self) -> None:
        self.active = False
        self.respawn_timer = random.uniform(18, 35)

    def update(self, dt: float) -> None:
        if not self.active:
            self.respawn_timer -= dt
            if self.respawn_timer <= 0:
                self.active = True

    def draw(self, surface: pygame.Surface, camera: pygame.Vector2) -> None:
        if not self.active:
            return
        pos = self.position - camera
        rect = pygame.Rect(0, 0, 25, 19)
        rect.center = pos
        pygame.draw.rect(surface, (113, 67, 36), rect, border_radius=4)
        pygame.draw.rect(surface, COLORS["gold"], rect, 3, border_radius=4)
        pygame.draw.circle(surface, COLORS["gold"], pos, 3)
