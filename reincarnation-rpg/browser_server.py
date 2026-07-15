"""Single-port browser game host for local play and public HTTPS tunnels."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import math
import random
import time
import uuid
from pathlib import Path

from aiohttp import WSMsgType, web

import coop_server
from echo_learning import EchoQLearner


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "browser"
SAVE_PATH = ROOT / "browser_saves.json"
ECHO_BRAIN_PATH = ROOT / "echo_brain_q.json"


class BrowserWorldState(coop_server.CoopState):
    NPCS = [
        {"id": "guide", "name": "Mira", "role": "Quest Weaver", "x": 455.0, "y": 330.0, "color": [255, 220, 120]},
        {"id": "smith", "name": "Bram", "role": "Relic Smith", "x": 335.0, "y": 480.0, "color": [255, 135, 82]},
        {"id": "trainer", "name": "Sera", "role": "Skill Trainer", "x": 535.0, "y": 485.0, "color": [140, 225, 255]},
    ]
    STYLE_STATS = {
        "Vanguard": (120, 40, [255, 166, 92]),
        "Spellblade": (95, 60, [142, 122, 255]),
        "Strider": (100, 45, [116, 235, 155]),
    }
    FLOOR_BOSSES = [
        {
            "name": "Asterion, Skyglass Sentinel",
            "x": 1656.0,
            "y": 600.0,
            "hp": 850,
            "color": [66, 215, 228],
            "shape": "sentinel",
        },
        {
            "name": "Nyxara, Ember Wyrm",
            "x": 2250.0,
            "y": 1240.0,
            "hp": 1250,
            "color": [255, 91, 82],
            "shape": "wyrm",
        },
        {
            "name": "Orinox, Chrono Knight",
            "x": 1160.0,
            "y": 1640.0,
            "hp": 1750,
            "color": [239, 184, 67],
            "shape": "knight",
        },
    ]
    MONSTER_TEMPLATES = [
        ("Slime", 620, 430, 45, 7, 72, [88, 218, 151], 18, 6),
        ("Fangling", 760, 520, 62, 10, 105, [235, 102, 104], 25, 9),
        ("Wisp", 920, 350, 52, 9, 92, [142, 122, 255], 24, 10),
        ("Slime", 1080, 670, 45, 7, 72, [88, 218, 151], 18, 6),
        ("Fangling", 1220, 420, 62, 10, 105, [235, 102, 104], 25, 9),
        ("Ash Warden", 1390, 720, 115, 17, 68, [255, 165, 72], 48, 18),
        ("Wisp", 1510, 390, 52, 9, 92, [142, 122, 255], 24, 10),
        ("Hollow Knight", 1770, 760, 145, 20, 65, [161, 138, 181], 60, 24),
        ("Cinder Mage", 1900, 470, 88, 16, 78, [225, 91, 207], 52, 22),
        ("Void Stalker", 2080, 680, 96, 18, 118, [188, 69, 224], 58, 24),
        ("Hollow Knight", 2300, 430, 145, 20, 65, [161, 138, 181], 60, 24),
        ("Void Stalker", 2520, 810, 96, 18, 118, [188, 69, 224], 58, 24),
    ]

    def __init__(self, max_players: int = 4, save_path: Path | None = None):
        super().__init__(max_players)
        self.save_path = save_path
        self.saved_characters = {}
        if save_path and save_path.exists():
            try:
                self.saved_characters = json.loads(save_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self.saved_characters = {}
        self.monsters = []
        for index, template in enumerate(self.MONSTER_TEMPLATES):
            kind, x, y, hp, attack, speed, color, xp, gold = template
            self.monsters.append(
                {
                    "id": f"monster-{index}",
                    "kind": kind,
                    "x": float(x),
                    "y": float(y),
                    "spawn_x": float(x),
                    "spawn_y": float(y),
                    "hp": hp,
                    "max_hp": hp,
                    "attack": attack,
                    "speed": speed,
                    "color": color,
                    "xp": xp,
                    "gold": gold,
                    "active": True,
                    "respawn_at": 0.0,
                    "attack_at": 0.0,
                    "unique": False,
                }
            )
        self.monsters.append(
            {
                "id": "unique-grimveil",
                "kind": "Grimveil Devourer",
                "x": 1420.0,
                "y": 1080.0,
                "spawn_x": 1420.0,
                "spawn_y": 1080.0,
                "hp": 700,
                "max_hp": 700,
                "attack": 28,
                "speed": 102,
                "color": [255, 72, 176],
                "xp": 320,
                "gold": 220,
                "active": False,
                "respawn_at": 1_000_000_000_000.0,
                "attack_at": 0.0,
                "unique": True,
            }
        )
        for index, (kind, x, y, hp, attack, color) in enumerate([
            ("Rift Crawler", 2320, 1380, 150, 20, [89, 190, 255]),
            ("Rune Sentinel", 2500, 1510, 210, 24, [185, 126, 255]),
            ("Rift Crawler", 2650, 1710, 150, 20, [89, 190, 255]),
            ("Vault Colossus", 2460, 1840, 480, 32, [255, 198, 91]),
        ]):
            self.monsters.append({"id": f"dungeon-{index}", "kind": kind, "x": float(x), "y": float(y), "spawn_x": float(x), "spawn_y": float(y), "hp": hp, "max_hp": hp, "attack": attack, "speed": 75, "color": color, "xp": 80 + index * 25, "gold": 35 + index * 12, "active": True, "respawn_at": 0.0, "attack_at": 0.0, "unique": False, "elite": index == 3, "zone": "dungeon"})
        self.unique_encounter = {
            "name": "Grimveil Devourer",
            "unlocked": False,
            "defeated": False,
            "requirement": "Complete 2 Hunt Quests",
        }
        self.loot: list[dict] = []
        self.echo = {
            "x": 470.0,
            "y": 445.0,
            "hp": 90,
            "max_hp": 90,
            "target": None,
            "target_name": None,
            "state": "patrolling",
            "attack_pulse": 0,
            "energy": 60.0,
            "max_energy": 60,
            "deaths": 0,
            "current_action": "patrol",
            "kills": 0,
            "damage": 0,
            "boss_damage": 0,
            "support_seconds": 0.0,
        }
        self.echo_patrol_angle = 0.0
        self.echo_learner = EchoQLearner(ECHO_BRAIN_PATH if save_path else None)
        self.echo_decision_timer = 0.0
        self.echo_previous_state: str | None = None
        self.echo_previous_action: str | None = None
        self.echo_pending_reward = 0.0
        self.echo_decision_position = (self.echo["x"], self.echo["y"])
        self.echo_explore_goal = (900.0, 600.0)
        self.echo_tiles: set[str] = set()
        self.floor_number = 1
        self.guardian: dict = {}
        self.next_guardian_at = 0.0
        self.guardian_attack_at = 0.0
        self.guardian_special_at = time.monotonic() + 6
        self.chests = [
            {"id": "vault-a", "x": 2275.0, "y": 1280.0, "opened_by": []},
            {"id": "vault-b", "x": 2690.0, "y": 1880.0, "opened_by": []},
        ]
        self.last_save_at = time.monotonic()
        self._spawn_guardian(1)

    def _spawn_guardian(self, floor_number: int) -> None:
        template = self.FLOOR_BOSSES[(floor_number - 1) % len(self.FLOOR_BOSSES)]
        cycle = (floor_number - 1) // len(self.FLOOR_BOSSES)
        maximum = int(template["hp"] * (1 + cycle * 0.35))
        self.floor_number = floor_number
        self.guardian = {
            "name": template["name"],
            "x": template["x"],
            "y": template["y"],
            "hp": maximum,
            "max_hp": maximum,
            "color": template["color"],
            "shape": template["shape"],
            "floor": floor_number,
            "cleared": False,
            "next_spawn_seconds": 0,
            "phase": 1,
            "special_warning": False,
            "special_seconds": 6.0,
        }
        self.floor_cleared = False
        self.next_guardian_at = 0.0
        self.guardian_special_at = time.monotonic() + 6

    def join(self, name: str, style: str = "Vanguard") -> dict:
        welcome = super().join(name)
        with self.lock:
            player = self.players[welcome["player_id"]]
            style = style if style in self.STYLE_STATS else "Vanguard"
            style_hp, style_mana, style_color = self.STYLE_STATS[style]
            player.update({"xp": 0, "xp_next": 100, "gold": 0, "kills": 0, "style": style, "color": style_color})
            player["floors_cleared"] = 0
            player["base_max_hp"] = style_hp
            player["hp"] = style_hp
            player["max_hp"] = style_hp
            player["mana"] = style_mana
            player["max_mana"] = style_mana
            player["last_skill"] = 0.0
            player["last_devourer"] = 0.0
            player["quest_kills"] = 0
            player["quest_target"] = 5
            player["quest_completions"] = 0
            player["essences"] = {}
            player["evolution_points"] = 0
            player["evolution_rank"] = "Reborn Wanderer"
            player["devourer_unlocked"] = False
            player["inventory"] = []
            player["equipment"] = {"weapon": None, "armor": None, "charm": None}
            player["attack_bonus"] = 0
            player["defense"] = 0
            player["dungeon_chests"] = 0
            player["story_chapter"] = "Chapter 1: A Voice Beyond the Gate"
            player["story_objective"] = "Speak with Mira in Everdawn Village (F)."
            player["notice"] = "Welcome, reborn traveler. Your character will save automatically."
            player["notice_id"] = 1
            saved = self.saved_characters.get(player["name"].casefold())
            if saved:
                for key in ("xp", "xp_next", "gold", "kills", "floors_cleared", "base_max_hp", "max_mana", "quest_kills", "quest_target", "quest_completions", "essences", "evolution_points", "evolution_rank", "devourer_unlocked", "inventory", "equipment", "dungeon_chests", "style", "story_chapter", "story_objective"):
                    if key in saved:
                        player[key] = saved[key]
                player["hp"], player["mana"] = player["base_max_hp"], player["max_mana"]
                player["notice"] = "Saved character restored. Welcome back."
            self._recalculate_equipment(player)
            welcome["snapshot"] = self.snapshot()
        return welcome

    def _recalculate_equipment(self, player: dict) -> None:
        equipped = [item for item in player["equipment"].values() if item]
        player["attack_bonus"] = sum(item.get("attack", 0) for item in equipped)
        player["defense"] = sum(item.get("defense", 0) for item in equipped)
        player["max_hp"] = player["base_max_hp"] + sum(item.get("hp", 0) for item in equipped)
        player["hp"] = min(player["hp"], player["max_hp"])

    def _new_item(self, power: int = 1, minimum_rarity: int = 0) -> dict:
        rarities = [("Common", 1.0, [190, 205, 215]), ("Uncommon", 1.35, [92, 224, 137]), ("Rare", 1.8, [91, 169, 255]), ("Epic", 2.5, [195, 112, 255]), ("Legendary", 3.6, [255, 190, 65])]
        roll = random.random()
        rarity_index = max(minimum_rarity, 4 if roll < .015 else 3 if roll < .06 else 2 if roll < .18 else 1 if roll < .45 else 0)
        rarity, multiplier, color = rarities[rarity_index]
        slot = random.choice(["weapon", "armor", "charm"])
        names = {"weapon": ["Skyglass Blade", "Rift Spear", "Echo Fang"], "armor": ["Dawnweave Coat", "Runic Plate", "Mist Mantle"], "charm": ["Soul Prism", "Ember Ring", "Chrono Sigil"]}
        score = max(1, int((power + 2) * multiplier))
        return {"id": uuid.uuid4().hex[:10], "name": random.choice(names[slot]), "slot": slot, "rarity": rarity, "color": color, "attack": score if slot == "weapon" else score // 3, "defense": score if slot == "armor" else score // 3, "hp": score * 3 if slot == "charm" else 0}

    def _save_player(self, player: dict) -> None:
        if not self.save_path:
            return
        keys = ("xp", "xp_next", "gold", "kills", "floors_cleared", "base_max_hp", "max_mana", "quest_kills", "quest_target", "quest_completions", "essences", "evolution_points", "evolution_rank", "devourer_unlocked", "inventory", "equipment", "dungeon_chests", "style", "story_chapter", "story_objective")
        self.saved_characters[player["name"].casefold()] = {key: player[key] for key in keys}

    def save_all(self) -> None:
        if not self.save_path:
            return
        for player in self.players.values():
            self._save_player(player)
        temporary = self.save_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.saved_characters, indent=2), encoding="utf-8")
        temporary.replace(self.save_path)

    def leave(self, player_id: str) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if player:
                self._save_player(player)
                self.save_all()
            super().leave(player_id)

    def update_player(self, player_id: str, message: dict) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            authoritative = (player["hp"], player["max_hp"], player["level"])
            super().update_player(player_id, message)
            player["hp"], player["max_hp"], player["level"] = authoritative

    @staticmethod
    def in_safe_zone(x: float, y: float) -> bool:
        return math.dist((x, y), coop_server.SPAWN_POSITION) < 155

    def attack(self, player_id: str, message: dict) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            now = time.monotonic()
            if now - player["last_attack"] < 0.18:
                return
            target_id = str(message.get("target_id", ""))
            if target_id == "guardian":
                self.attack_guardian(player_id, message)
                return
            monster = next(
                (item for item in self.monsters if item["id"] == target_id and item["active"]),
                None,
            )
            if not monster or math.dist((player["x"], player["y"]), (monster["x"], monster["y"])) > 125:
                return
            damage = min(140, 17 + player["level"] * 3 + player["attack_bonus"])
            monster["hp"] = max(0, monster["hp"] - damage)
            player["last_attack"] = now
            if monster["hp"] == 0:
                self._defeat_monster(monster, player)

    def attack_guardian(self, player_id: str, message: dict) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player or self.floor_cleared:
                return
            now = time.monotonic()
            if now - player["last_attack"] < 0.18:
                return
            if math.dist(
                (player["x"], player["y"]),
                (self.guardian["x"], self.guardian["y"]),
            ) > 190:
                return
            damage = min(165, 20 + player["level"] * 4 + player["attack_bonus"])
            self.guardian["hp"] = max(0, self.guardian["hp"] - damage)
            player["last_attack"] = now
            if self.guardian["hp"] == 0:
                self.floor_cleared = True
                self.guardian["cleared"] = True
                self.next_guardian_at = now + 8
                player["floors_cleared"] += 1
                player["gold"] += 150 * self.floor_number
                player["xp"] += 250 * self.floor_number

    def use_skill(self, player_id: str) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            now = time.monotonic()
            if now - player["last_skill"] < 1.2 or player["mana"] < 15:
                return
            player["last_skill"] = now
            player["mana"] -= 15
            damage = min(100, 34 + player["level"] * 3 + player["attack_bonus"])
            for monster in self.monsters:
                if (
                    monster["active"]
                    and math.dist(
                        (player["x"], player["y"]),
                        (monster["x"], monster["y"]),
                    ) < 175
                ):
                    monster["hp"] = max(0, monster["hp"] - damage)
                    if monster["hp"] == 0:
                        self._defeat_monster(monster, player)
            if (
                not self.floor_cleared
                and math.dist(
                    (player["x"], player["y"]),
                    (self.guardian["x"], self.guardian["y"]),
                ) < 205
            ):
                self.guardian["hp"] = max(0, self.guardian["hp"] - damage)
                if self.guardian["hp"] == 0:
                    self.floor_cleared = True
                    self.guardian["cleared"] = True
                    self.next_guardian_at = now + 8
                    player["floors_cleared"] += 1

    def use_devourer_skill(self, player_id: str) -> None:
        """An unlockable essence skill that damages nearby enemies and heals its user."""
        with self.lock:
            player = self.players.get(player_id)
            if not player or not player["devourer_unlocked"]:
                return
            now = time.monotonic()
            if now - player["last_devourer"] < 3.0 or player["mana"] < 25:
                return
            player["last_devourer"] = now
            player["mana"] -= 25
            damage = min(145, 52 + player["level"] * 4 + player["attack_bonus"])
            total_dealt = 0
            for monster in self.monsters:
                if monster["active"] and math.dist(
                    (player["x"], player["y"]), (monster["x"], monster["y"])
                ) < 260:
                    dealt = min(monster["hp"], damage)
                    monster["hp"] -= dealt
                    total_dealt += dealt
                    if monster["hp"] == 0:
                        self._defeat_monster(monster, player)
            if not self.floor_cleared and math.dist(
                (player["x"], player["y"]),
                (self.guardian["x"], self.guardian["y"]),
            ) < 280:
                dealt = min(self.guardian["hp"], damage)
                self.guardian["hp"] -= dealt
                total_dealt += dealt
                if self.guardian["hp"] == 0:
                    self.floor_cleared = True
                    self.guardian["cleared"] = True
                    self.next_guardian_at = now + 8
                    player["floors_cleared"] += 1
            player["hp"] = min(player["max_hp"], player["hp"] + total_dealt * 0.18)

    @staticmethod
    def evolution_rank(points: int) -> str:
        if points >= 30:
            return "Worldshaper"
        if points >= 15:
            return "Apex Reborn"
        if points >= 5:
            return "Essence Adept"
        return "Reborn Wanderer"

    def equip_item(self, player_id: str, item_id: str) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            item = next((item for item in player["inventory"] if item["id"] == item_id), None)
            if not item:
                return
            old = player["equipment"].get(item["slot"])
            player["inventory"].remove(item)
            if old:
                player["inventory"].append(old)
            player["equipment"][item["slot"]] = item
            self._recalculate_equipment(player)
            player["notice"] = f"Equipped {item['rarity']} {item['name']}."
            player["notice_id"] += 1

    def interact(self, player_id: str) -> None:
        with self.lock:
            player = self.players.get(player_id)
            if not player:
                return
            nearby_npc = next((npc for npc in self.NPCS if math.dist((player["x"], player["y"]), (npc["x"], npc["y"])) < 95), None)
            if nearby_npc:
                if nearby_npc["id"] == "guide":
                    player["story_chapter"] = "Chapter 1: The Fractured Crown"
                    player["story_objective"] = "Complete 2 Hunt Quests and awaken the hidden Unique."
                    player["notice"] = "Mira: The world remembers your former life. Hunt, evolve, and seek the sealed vault."
                elif nearby_npc["id"] == "smith":
                    if player["gold"] >= 75 and len(player["inventory"]) < 24:
                        player["gold"] -= 75
                        item = self._new_item(player["level"] + 2, 1)
                        player["inventory"].append(item)
                        player["notice"] = f"Bram forged {item['rarity']} {item['name']}. Open Inventory (I)."
                    else:
                        player["notice"] = "Bram: Forging costs 75 gold and requires inventory space."
                else:
                    player["hp"], player["mana"] = player["max_hp"], player["max_mana"]
                    player["notice"] = "Sera restored you. Your equipped gear now strengthens server-authoritative combat."
                player["notice_id"] += 1
                return
            nearby_chest = next((chest for chest in self.chests if math.dist((player["x"], player["y"]), (chest["x"], chest["y"])) < 90 and player["name"].casefold() not in chest["opened_by"]), None)
            if nearby_chest:
                nearby_chest["opened_by"].append(player["name"].casefold())
                item = self._new_item(player["level"] + 4, 2)
                player["inventory"].append(item)
                player["dungeon_chests"] += 1
                player["notice"] = f"Vault opened: {item['rarity']} {item['name']} acquired!"
                player["notice_id"] += 1
                return
            player["notice"] = "Nothing nearby to interact with. Look for NPCs or glowing vault chests."
            player["notice_id"] += 1

    def _update_story(self, player: dict) -> None:
        if player["floors_cleared"] >= 3:
            player["story_chapter"] = "Chapter 5: Beyond Ascension"
            player["story_objective"] = "Climb higher floors and master every evolution path."
        elif player["dungeon_chests"]:
            player["story_chapter"] = "Chapter 4: Relic Below"
            player["story_objective"] = "Defeat the Vault Colossus and clear Floor 3."
        elif self.unique_encounter["defeated"]:
            player["story_chapter"] = "Chapter 3: Gate of Ash"
            player["story_objective"] = "Enter the southeastern dungeon and open a relic vault (F)."
        elif player["quest_completions"] >= 2:
            player["story_chapter"] = "Chapter 2: Grimveil Awakens"
            player["story_objective"] = "Find and defeat the Grimveil Devourer."

    def _defeat_monster(self, monster: dict, player: dict | None) -> None:
        monster["active"] = False
        monster["respawn_at"] = time.monotonic() + random.uniform(7, 12)
        gear_drop = random.random() < (.65 if monster.get("elite") or monster.get("unique") else .28)
        drop = {
                "id": uuid.uuid4().hex[:9],
                "x": monster["x"],
                "y": monster["y"],
                "kind": "gear" if gear_drop else "potion" if random.random() < 0.22 else "gold",
                "value": monster["gold"],
                "expires_at": time.monotonic() + 25,
            }
        if gear_drop:
            drop["item"] = self._new_item(player["level"] if player else 1, 2 if monster.get("unique") or monster.get("elite") else 0)
        self.loot.append(drop)
        if monster.get("unique"):
            self.unique_encounter["defeated"] = True
            monster["respawn_at"] = 1_000_000_000_000.0
        if player:
            player["xp"] += monster["xp"]
            player["kills"] += 1
            player["quest_kills"] += 1
            essence_name = monster["kind"]
            player["essences"][essence_name] = player["essences"].get(essence_name, 0) + 1
            player["evolution_points"] += 5 if monster.get("unique") else 1
            player["evolution_rank"] = self.evolution_rank(player["evolution_points"])
            player["devourer_unlocked"] = player["evolution_points"] >= 5
            if player["quest_kills"] >= player["quest_target"]:
                player["quest_kills"] -= player["quest_target"]
                player["quest_completions"] += 1
                player["gold"] += 50 + player["quest_completions"] * 10
                player["xp"] += 75
                player["quest_target"] += 2
            while player["xp"] >= player["xp_next"]:
                player["xp"] -= player["xp_next"]
                player["level"] += 1
                player["xp_next"] = int(player["xp_next"] * 1.35)
                player["base_max_hp"] += 12
                self._recalculate_equipment(player)
                player["hp"] = player["max_hp"]
        else:
            self.echo["kills"] += 1

    def _echo_context(self, target: dict | None, players: list[dict]) -> tuple[str, list[str]]:
        health_ratio = self.echo["hp"] / self.echo["max_hp"]
        health = "critical" if health_ratio < 0.3 else "hurt" if health_ratio < 0.65 else "healthy"
        energy = "low" if self.echo["energy"] < 20 else "ready"
        ally_near = any(math.dist((self.echo["x"], self.echo["y"]), (player["x"], player["y"])) < 180 for player in players)
        if not target:
            state = f"hp={health}|energy={energy}|range=none|threat=none|ally={'yes' if ally_near else 'no'}"
            return state, ["patrol", "support"] if players else ["patrol"]
        distance = math.dist((self.echo["x"], self.echo["y"]), (target["x"], target["y"]))
        enemy_range = "close" if distance <= 46 else "near" if distance <= 180 else "far"
        threat = "unique" if target.get("unique") else "elite" if target.get("elite") else "normal"
        state = f"hp={health}|energy={energy}|range={enemy_range}|threat={threat}|ally={'yes' if ally_near else 'no'}"
        if enemy_range == "close":
            actions = ["strike", "circle", "retreat"]
            if self.echo["energy"] >= 20:
                actions.append("power")
        else:
            actions = ["approach", "explore"]
            if players:
                actions.append("support")
        return state, actions

    def _move_echo_toward(self, x: float, y: float, speed: float, dt: float) -> float:
        distance = math.dist((self.echo["x"], self.echo["y"]), (x, y))
        if distance > 0:
            step = min(distance, speed * dt)
            self.echo["x"] += (x - self.echo["x"]) / distance * step
            self.echo["y"] += (y - self.echo["y"]) / distance * step
            self.echo["x"] = max(35, min(2845, self.echo["x"]))
            self.echo["y"] = max(35, min(2077, self.echo["y"]))
        return distance

    def _tick_echo(self, active: list[dict], players: list[dict], dt: float) -> None:
        target = min(active, key=lambda item: math.dist((self.echo["x"], self.echo["y"]), (item["x"], item["y"]))) if active else None
        self.echo["target"] = target["id"] if target else None
        self.echo["target_name"] = target["kind"] if target else None
        state, valid_actions = self._echo_context(target, players)
        self.echo_decision_timer -= dt
        if self.echo_decision_timer <= 0:
            if self.echo_previous_state and self.echo_previous_action:
                moved = math.dist(self.echo_decision_position, (self.echo["x"], self.echo["y"]))
                if self.echo_previous_action in {"approach", "explore", "support", "retreat"} and moved < 2:
                    self.echo_pending_reward -= 0.45
                self.echo_learner.learn(
                    self.echo_previous_state,
                    self.echo_previous_action,
                    self.echo_pending_reward,
                    state,
                    valid_actions,
                )
            action = self.echo_learner.choose_action(state, valid_actions)
            self.echo_previous_state = state
            self.echo_previous_action = action
            self.echo_pending_reward = 0.0
            self.echo_decision_position = (self.echo["x"], self.echo["y"])
            self.echo_decision_timer = 0.35
        action = self.echo_previous_action or valid_actions[0]
        self.echo["current_action"] = action
        self.echo["state"] = action
        self.echo["energy"] = min(self.echo["max_energy"], self.echo["energy"] + 7 * dt)

        if action == "support" and players:
            ally = min(players, key=lambda player: math.dist((self.echo["x"], self.echo["y"]), (player["x"], player["y"])))
            distance = self._move_echo_toward(ally["x"], ally["y"], 115, dt)
            if distance < 180:
                self.echo_pending_reward += 0.7 * dt
                self.echo["hp"] = min(self.echo["max_hp"], self.echo["hp"] + 4 * dt)
        elif action in {"patrol", "explore"}:
            if action == "patrol":
                self.echo_patrol_angle += dt * 0.7
                goal = (470 + math.cos(self.echo_patrol_angle) * 90, 445 + math.sin(self.echo_patrol_angle) * 70)
            else:
                if math.dist((self.echo["x"], self.echo["y"]), self.echo_explore_goal) < 60:
                    self.echo_explore_goal = (self.echo_learner.random.uniform(300, 2650), self.echo_learner.random.uniform(260, 1900))
                goal = self.echo_explore_goal
            self._move_echo_toward(*goal, 95 if action == "patrol" else 125, dt)
        elif target:
            distance = math.dist((self.echo["x"], self.echo["y"]), (target["x"], target["y"]))
            if action == "approach" or (action in {"strike", "circle", "power"} and distance > 48):
                self._move_echo_toward(target["x"], target["y"], 135, dt)
                if action != "approach":
                    self.echo_pending_reward -= 0.08 * dt
            elif action == "retreat":
                if distance > 0:
                    away_x = self.echo["x"] + (self.echo["x"] - target["x"]) / distance * 150
                    away_y = self.echo["y"] + (self.echo["y"] - target["y"]) / distance * 150
                    self._move_echo_toward(away_x, away_y, 155, dt)
                self.echo["hp"] = min(self.echo["max_hp"], self.echo["hp"] + 2 * dt)
            else:
                dealt_rate = {"strike": 23, "circle": 17, "power": 34}[action]
                if action == "power":
                    self.echo["energy"] = max(0, self.echo["energy"] - 24 * dt)
                if distance > 0:
                    dx = (target["x"] - self.echo["x"]) / distance
                    dy = (target["y"] - self.echo["y"]) / distance
                    orbit_speed = 52 if action == "circle" else 18
                    self.echo["x"] += (-dy * orbit_speed + dx * (distance - 32) * 2) * dt
                    self.echo["y"] += (dx * orbit_speed + dy * (distance - 32) * 2) * dt
                dealt = min(target["hp"], dealt_rate * dt)
                target["hp"] -= dealt
                self.echo["damage"] += dealt
                self.echo["attack_pulse"] += 1
                self.echo_pending_reward += dealt * 0.045
                risk = {"strike": 0.32, "circle": 0.12, "power": 0.52}[action]
                incoming = target["attack"] * risk * dt
                self.echo["hp"] -= incoming
                self.echo_pending_reward -= incoming * 0.07
                if target["hp"] <= 0:
                    self.echo_pending_reward += 15 if target.get("unique") else 10 if target.get("elite") else 7
                    self._defeat_monster(target, None)

        if self.echo["hp"] <= 0:
            self.echo_pending_reward -= 20
            self.echo_learner.learn(state, action, self.echo_pending_reward, state, [], terminal=True)
            self.echo["x"], self.echo["y"] = 470.0, 445.0
            self.echo["hp"] = self.echo["max_hp"]
            self.echo["energy"] = self.echo["max_energy"]
            self.echo["deaths"] += 1
            self.echo_previous_state = None
            self.echo_previous_action = None
            self.echo_pending_reward = 0.0
            self.echo_decision_timer = 0.0

    def tick(self, dt: float) -> None:
        with self.lock:
            now = time.monotonic()
            if self.floor_cleared and self.next_guardian_at:
                remaining = max(0, self.next_guardian_at - now)
                self.guardian["next_spawn_seconds"] = round(remaining, 1)
                if remaining == 0:
                    self._spawn_guardian(self.floor_number + 1)
            living_players = list(self.players.values())
            if (
                not self.unique_encounter["unlocked"]
                and sum(player["quest_completions"] for player in living_players) >= 2
            ):
                self.unique_encounter["unlocked"] = True
                unique = next(
                    monster for monster in self.monsters if monster.get("unique")
                )
                unique["active"] = True
                unique["hp"] = unique["max_hp"]
            for player in living_players:
                self._update_story(player)
                player["mana"] = min(
                    player["max_mana"], player["mana"] + 6 * dt
                )
                if self.in_safe_zone(player["x"], player["y"]):
                    player["hp"] = min(
                        player["max_hp"], player["hp"] + 12 * dt
                    )
            for monster in self.monsters:
                if not monster["active"]:
                    if now >= monster["respawn_at"]:
                        monster["active"] = True
                        monster["hp"] = monster["max_hp"]
                        monster["x"], monster["y"] = monster["spawn_x"], monster["spawn_y"]
                    continue
                targets = [p for p in living_players if not self.in_safe_zone(p["x"], p["y"])]
                if not targets:
                    continue
                target = min(targets, key=lambda p: math.dist((p["x"], p["y"]), (monster["x"], monster["y"])))
                distance = math.dist((target["x"], target["y"]), (monster["x"], monster["y"]))
                if distance < 520 and distance > 30:
                    monster["x"] += (target["x"] - monster["x"]) / distance * monster["speed"] * dt
                    monster["y"] += (target["y"] - monster["y"]) / distance * monster["speed"] * dt
                elif distance <= 30 and now >= monster["attack_at"]:
                    target["hp"] -= max(1, monster["attack"] - target["defense"])
                    monster["attack_at"] = now + 0.9
                    if target["hp"] <= 0:
                        target["x"], target["y"] = coop_server.SPAWN_POSITION
                        target["hp"] = target["max_hp"]
                        target["gold"] = max(0, target["gold"] - 10)

            active = [monster for monster in self.monsters if monster["active"]]
            self._tick_echo(active, living_players, dt)

            echo_tile = f"{int(self.echo['x'] // 96)},{int(self.echo['y'] // 96)}"
            if echo_tile not in self.echo_tiles:
                self.echo_pending_reward += 0.4
            self.echo_tiles.add(echo_tile)
            if any(
                math.dist((self.echo["x"], self.echo["y"]), (p["x"], p["y"])) < 180
                for p in living_players
            ):
                self.echo["support_seconds"] += dt
                self.echo_pending_reward += 0.15 * dt

            if not self.floor_cleared:
                boss_distance = math.dist(
                    (self.echo["x"], self.echo["y"]),
                    (self.guardian["x"], self.guardian["y"]),
                )
                if boss_distance < 70:
                    dealt = min(self.guardian["hp"], 10 * dt)
                    self.guardian["hp"] -= dealt
                    self.echo["boss_damage"] += dealt
                    self.echo_pending_reward += dealt * 0.06
                    if self.guardian["hp"] == 0:
                        self.floor_cleared = True
                        self.guardian["cleared"] = True
                        self.next_guardian_at = now + 8

            self.loot = [item for item in self.loot if now < item["expires_at"]]
            for item in list(self.loot):
                collector = next(
                    (p for p in living_players if math.dist((p["x"], p["y"]), (item["x"], item["y"])) < 34),
                    None,
                )
                if collector:
                    if item["kind"] == "potion":
                        collector["hp"] = min(collector["max_hp"], collector["hp"] + 45)
                    elif item["kind"] == "gear":
                        if len(collector["inventory"]) < 24:
                            collector["inventory"].append(item["item"])
                            collector["notice"] = f"Loot: {item['item']['rarity']} {item['item']['name']}"
                            collector["notice_id"] += 1
                    else:
                        collector["gold"] += item["value"]
                    self.loot.remove(item)

            if not self.floor_cleared and living_players:
                ratio = self.guardian["hp"] / self.guardian["max_hp"]
                self.guardian["phase"] = 3 if ratio <= .3 else 2 if ratio <= .65 else 1
                special_remaining = self.guardian_special_at - now
                self.guardian["special_seconds"] = round(max(0, special_remaining), 1)
                self.guardian["special_warning"] = 0 < special_remaining <= 1.25
                if special_remaining <= 0:
                    radius = 175 + self.guardian["phase"] * 35
                    for victim in living_players:
                        if math.dist((victim["x"], victim["y"]), (self.guardian["x"], self.guardian["y"])) < radius:
                            victim["hp"] -= max(4, 14 + self.floor_number * 4 + self.guardian["phase"] * 5 - victim["defense"])
                    self.guardian_special_at = now + max(3.4, 6.2 - self.guardian["phase"] * .7)
                    self.guardian["special_warning"] = False
                target = min(
                    living_players,
                    key=lambda p: math.dist(
                        (p["x"], p["y"]),
                        (self.guardian["x"], self.guardian["y"]),
                    ),
                )
                distance = math.dist(
                    (target["x"], target["y"]),
                    (self.guardian["x"], self.guardian["y"]),
                )
                if (
                    distance < 88
                    and now >= self.guardian_attack_at
                    and not self.in_safe_zone(target["x"], target["y"])
                ):
                    target["hp"] -= max(2, 16 + self.floor_number * 5 - target["defense"])
                    self.guardian_attack_at = now + 0.9
                    if target["hp"] <= 0:
                        target["x"], target["y"] = coop_server.SPAWN_POSITION
                        target["hp"] = target["max_hp"]
            if self.save_path and now - self.last_save_at >= 5:
                self.save_all()
                self.echo_learner.save()
                self.last_save_at = now

    def snapshot(self) -> dict:
        payload = super().snapshot()
        with self.lock:
            payload.update(
                {
                    "guardian": dict(self.guardian),
                    "monsters": [dict(monster) for monster in self.monsters],
                    "loot": [dict(item) for item in self.loot],
                    "echo": dict(self.echo),
                    "echo_progress": self.echo_progress(),
                    "echo_learning": self.echo_learner.snapshot(self.echo_previous_state),
                    "unique_encounter": dict(self.unique_encounter),
                    "npcs": [dict(npc) for npc in self.NPCS],
                    "chests": [{"id": chest["id"], "x": chest["x"], "y": chest["y"]} for chest in self.chests],
                }
            )
        return payload

    def echo_progress(self) -> dict[str, float | bool]:
        exploration = min(1.0, len(self.echo_tiles) / 120)
        monsters = min(1.0, self.echo["kills"] / 75)
        combat = min(1.0, self.echo["damage"] / 8000)
        boss = min(1.0, self.echo["boss_damage"] / 5000)
        support = min(1.0, self.echo["support_seconds"] / 300)
        overall = (
            exploration * 0.25
            + monsters * 0.20
            + combat * 0.20
            + boss * 0.20
            + support * 0.15
        )
        return {
            "overall": overall,
            "exploration": exploration,
            "monsters": monsters,
            "combat": combat,
            "boss": boss,
            "support": support,
            "ready_for_content": overall >= 0.85,
        }


async def index_handler(request: web.Request) -> web.FileResponse:
    return web.FileResponse(WEB_ROOT / "index.html")


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(heartbeat=20, max_msg_size=65536)
    await ws.prepare(request)
    player_id = None
    try:
        first = await ws.receive_json(timeout=10)
        if first.get("type") != "join":
            await ws.send_json({"type": "error", "message": "Join required"})
            return ws
        welcome = coop_server.STATE.join(first.get("name", "Adventurer"), first.get("style", "Vanguard"))
        player_id = welcome["player_id"]
        await ws.send_str(json.dumps(welcome, separators=(",", ":")))
        async for message in ws:
            if message.type == WSMsgType.TEXT:
                payload = json.loads(message.data)
                kind = payload.get("type")
                if kind == "state":
                    coop_server.STATE.update_player(player_id, payload)
                elif kind == "attack_guardian":
                    coop_server.STATE.attack_guardian(player_id, payload)
                elif kind == "attack":
                    coop_server.STATE.attack(player_id, payload)
                elif kind == "skill":
                    coop_server.STATE.use_skill(player_id)
                elif kind == "devourer_skill":
                    coop_server.STATE.use_devourer_skill(player_id)
                elif kind == "equip":
                    coop_server.STATE.equip_item(player_id, str(payload.get("item_id", "")))
                elif kind == "interact":
                    coop_server.STATE.interact(player_id)
                await ws.send_str(
                    json.dumps(coop_server.STATE.snapshot(), separators=(",", ":"))
                )
            elif message.type == WSMsgType.ERROR:
                break
    except (TimeoutError, ValueError, json.JSONDecodeError):
        pass
    finally:
        if player_id:
            coop_server.STATE.leave(player_id)
    return ws


async def world_loop(app: web.Application):
    async def tick_forever():
        while True:
            coop_server.STATE.tick(0.05)
            await asyncio.sleep(0.05)

    task = asyncio.create_task(tick_forever())
    yield
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    coop_server.STATE.save_all()
    coop_server.STATE.echo_learner.save()


def make_app(max_players: int, save_path: Path | None = SAVE_PATH) -> web.Application:
    coop_server.STATE = BrowserWorldState(max_players, save_path)
    app = web.Application(client_max_size=65536)
    app.cleanup_ctx.append(world_loop)
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_static("/", WEB_ROOT, show_index=False)
    return app


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--max-players", type=int, default=4)
    parser.add_argument("--no-save", action="store_true", help="Disable character persistence for automated tests.")
    args = parser.parse_args()
    print(f"Everdawn browser game: http://127.0.0.1:{args.port}")
    print(f"HTTP and WebSockets share port {args.port}.")
    web.run_app(
        make_app(args.max_players, None if args.no_save else SAVE_PATH),
        host=args.host,
        port=args.port,
        print=None,
        access_log=None,
    )


if __name__ == "__main__":
    main()
