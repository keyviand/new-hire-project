from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import pygame

from entities import (
    Hero,
    Treasure,
    make_boss,
    make_chapter2_enemy,
    make_enemy,
    make_floor_guardian,
)
from learning_ai import LearningAdventurer
from settings import COLORS, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIZE, TITLE
from world import World


ROOT = Path(__file__).resolve().parent


class Game:
    def __init__(self, headless: bool = False, network_client=None, player_name: str = "Ari"):
        pygame.init()
        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 25)
        self.small_font = pygame.font.Font(None, 20)
        self.large_font = pygame.font.Font(None, 48)
        self.world = World()
        spawn = self.world.spawn_position()
        self.hero = Hero(x=spawn.x, y=spawn.y, color=COLORS["player"])
        self.hero.name = player_name[:18] or "Ari"
        self.network_client = network_client
        self.remote_players: list[dict] = []
        self.network_error_shown = False
        self.echo = LearningAdventurer(
            spawn.x + 80, spawn.y + 40, ROOT / "ai_brain_vrmmo.json"
        )
        self.enemies = []
        for difficulty, count in [(1, 12), (2, 10), (3, 6)]:
            for _ in range(count):
                x, y = self.world.random_walkable_tile(8 + difficulty * 2)
                self.enemies.append(make_enemy(x, y, difficulty))
        for _ in range(16):
            x, y = self.world.random_chapter2_tile()
            self.enemies.append(make_chapter2_enemy(x, y))
        self.boss = make_boss(*self.world.boss_tile)
        self.enemies.append(self.boss)
        self.boss_rewarded = False
        self.floor_guardian = make_floor_guardian(*self.world.floor_guardian_tile)
        self.enemies.append(self.floor_guardian)
        self.floor_guardian_rewarded = False
        self.treasures = []
        for index in range(12):
            x, y = self.world.random_walkable_tile(7)
            self.treasures.append(
                Treasure(
                    x=(x + 0.5) * TILE_SIZE,
                    y=(y + 0.5) * TILE_SIZE,
                    kind="potion" if index % 4 == 0 else "chest",
                    value=random.randint(10, 28),
                )
            )
        self.camera = pygame.Vector2()
        self.messages = [
            "Everdawn Online: enter Skyglass Fields, master sword skills, and defeat Asterion."
        ]
        self.running = True
        self.interaction_cooldown = 0.0
        self.show_progress = False
        self.show_player_menu = False
        self.parry_flash = 0.0

    def log(self, message: str) -> None:
        self.messages.append(message)
        self.messages = self.messages[-5:]

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_h:
                    self.log(self.hero.use_potion())
                elif event.key == pygame.K_q:
                    self.player_dodge()
                elif event.key == pygame.K_e:
                    self.player_spell()
                elif event.key == pygame.K_t:
                    self.echo.rescue(self.world, count_episode=False)
                    self.log("Echo was manually returned to the village.")
                elif event.key == pygame.K_p:
                    self.show_progress = not self.show_progress
                elif event.key == pygame.K_m:
                    self.show_player_menu = not self.show_player_menu
                elif event.key in {pygame.K_LSHIFT, pygame.K_RSHIFT}:
                    self.hero.parry_window = 0.28
                elif event.key == pygame.K_1:
                    self.sword_skill("linear")
                elif event.key == pygame.K_2:
                    self.sword_skill("cyclone")
                elif event.key == pygame.K_3:
                    self.sword_skill("vorpal")
                elif event.key == pygame.K_f:
                    self.interact()
                elif event.key == pygame.K_r:
                    shrine = pygame.Vector2(
                        (self.world.shrine_tile[0] + 0.5) * TILE_SIZE,
                        (self.world.shrine_tile[1] + 0.5) * TILE_SIZE,
                    )
                    if self.hero.position.distance_to(shrine) < 90:
                        self.log(self.hero.reincarnate(self.world.spawn_position()))
                    else:
                        self.log("Find the violet reincarnation shrine first.")
                elif event.key == pygame.K_F5:
                    self.save()
                    self.log("World saved.")
                elif event.key == pygame.K_F9:
                    self.load()

    def interact(self) -> None:
        quest = pygame.Vector2(
            (self.world.quest_tile[0] + 0.5) * TILE_SIZE,
            (self.world.quest_tile[1] + 0.5) * TILE_SIZE,
        )
        forge = pygame.Vector2(
            (self.world.forge_tile[0] + 0.5) * TILE_SIZE,
            (self.world.forge_tile[1] + 0.5) * TILE_SIZE,
        )
        gate = self.world.chapter2_position()
        portal = self.world.floor_portal_position()
        if self.hero.position.distance_to(forge) < 85:
            self.log(self.hero.upgrade_equipment())
        elif self.hero.position.distance_to(portal) < 90:
            if self.hero.floors_cleared >= 1:
                self.hero.current_floor = 2
                self.log("Floor 2 is unlocked. Its full region will arrive in the next update.")
            else:
                self.log("Defeat Asterion in the Skyglass arena to unlock Floor 2.")
        elif self.hero.position.distance_to(gate) < 95:
            self.log("The Ashen Reach lies ahead. The Obsidian Vault waits in the southeast.")
        elif self.hero.position.distance_to(quest) < 85:
            if self.hero.quest_kills >= self.hero.quest_target:
                self.hero.quest_kills -= self.hero.quest_target
                self.hero.gold += 40
                self.hero.potions += 2
                for event in self.hero.gain_xp(45):
                    self.log(event)
                self.hero.quest_target += 2
                self.log("Quest complete! Gold, potions, and experience awarded.")
            else:
                self.log(
                    f"Hunt monsters: {self.hero.quest_kills}/{self.hero.quest_target} defeated."
                )
        else:
            self.log("Nothing nearby to interact with.")

    def update(self, dt: float) -> None:
        self.sync_network()
        self.hero.update_timers(dt)
        self.parry_flash = max(0.0, self.parry_flash - dt)
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        if direction.length_squared():
            direction = direction.normalize()
            candidate = self.hero.position + direction * self.hero.speed * dt
            if self.world.walkable_pixel(candidate.x, self.hero.y):
                self.hero.x = candidate.x
            if self.world.walkable_pixel(self.hero.x, candidate.y):
                self.hero.y = candidate.y

        if keys[pygame.K_SPACE]:
            self.player_attack()

        if self.world.is_safe_zone(self.hero.x, self.hero.y):
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + 18 * dt)
            self.hero.mana = min(self.hero.max_mana, self.hero.mana + 12 * dt)

        for enemy in self.enemies:
            if enemy.boss and enemy.active:
                ratio = enemy.hp / enemy.max_hp
                enemy.phase = 3 if ratio < 0.30 else 2 if ratio < 0.65 else 1
                enemy.speed = 82 + (enemy.phase - 1) * 24
                enemy.attack = 24 + (enemy.phase - 1) * 7
                if enemy.floor_boss:
                    enemy.attack = 27 + (enemy.phase - 1) * 8
            enemy.update(dt, self.hero, self.world)
            distance = self.hero.distance_to(enemy)
            touching = distance < self.hero.radius + enemy.radius + 3
            ranged_hit = enemy.role == "skirmisher" and distance < enemy.attack_range
            if (
                enemy.active
                and enemy.attack_cooldown <= 0
                and self.hero.hurt_cooldown <= 0
                and (touching or ranged_hit)
                and not self.world.is_safe_zone(self.hero.x, self.hero.y)
            ):
                if self.hero.parry_window > 0:
                    self.hero.parry_window = 0
                    self.parry_flash = 0.24
                    enemy.attack_cooldown = 1.4
                    self.damage_enemy(enemy, 8 + self.hero.sword_mastery // 5)
                    self.hero.sword_mastery += 2
                    self.log(f"Perfect parry against {enemy.kind}!")
                else:
                    damage = max(1, int(enemy.attack * (1 - self.hero.damage_reduction)))
                    self.hero.hp -= damage
                self.hero.hurt_cooldown = 0.65
                enemy.attack_cooldown = 0.9 if ranged_hit else 0.65
                if self.hero.hp <= 0:
                    self.hero_death()
                    break

        for treasure in self.treasures:
            treasure.update(dt)
            if treasure.active and self.hero.position.distance_to(treasure.position) < 28:
                treasure.collect()
                self.hero.gold += treasure.value
                if treasure.kind == "potion":
                    self.hero.potions += 1
                    self.log("Found a potion cache.")
                else:
                    self.log(f"Opened a treasure chest: +{treasure.value} gold.")

        for message in self.echo.update(
            dt, self.world, self.enemies, self.treasures, self.hero
        ):
            self.log(message)
        self.apply_network_snapshot()

        if not self.boss.active and not self.boss_rewarded:
            self.boss_rewarded = True
            self.hero.boss_kills += 1
            self.hero.void_cores += 4
            self.hero.gold += 180
            self.log("The Hollow Sovereign fell. You received 4 void cores.")
        elif self.boss.active and self.boss.hp == self.boss.max_hp:
            self.boss_rewarded = False

        if not self.floor_guardian.active and not self.floor_guardian_rewarded:
            self.floor_guardian_rewarded = True
            self.hero.floors_cleared = max(1, self.hero.floors_cleared)
            self.hero.gold += 250
            self.hero.sword_mastery += 25
            self.log("Floor 1 cleared! Return to the cyan portal to unlock Floor 2.")
        if self.hero.floors_cleared >= 1:
            self.floor_guardian.active = False

        target = self.hero.position - pygame.Vector2(
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        )
        max_camera = pygame.Vector2(
            self.world.pixel_width - SCREEN_WIDTH,
            self.world.pixel_height - SCREEN_HEIGHT,
        )
        target.x = max(0, min(max_camera.x, target.x))
        target.y = max(0, min(max_camera.y, target.y))
        self.camera += (target - self.camera) * min(1, dt * 6)

    def player_attack(self) -> None:
        if self.hero.attack_cooldown > 0:
            return
        self.hero.attack_cooldown = 0.38
        target = min(
            (enemy for enemy in self.enemies if enemy.active),
            key=self.hero.distance_to,
            default=None,
        )
        if target is None or self.hero.distance_to(target) > 72:
            return
        self.hero.combo = min(5, self.hero.combo + 1)
        self.hero.combo_timer = 0.9
        combo_bonus = 1.0 + self.hero.combo * 0.08
        damage = int(
            (self.hero.attack + self.hero.legacy_power + self.hero.weapon_level * 2)
            * combo_bonus
        )
        self.hero.sword_mastery += 1
        self.damage_enemy(target, damage)
        if target.hp <= 0:
            target.defeat()
            self.hero.kills += 1
            self.hero.quest_kills += 1
            self.hero.gold += target.gold_reward
            if target.kind == "Ash Warden":
                self.hero.soul_shards += 1
            if target.chapter == 2:
                self.hero.void_cores += 1
            for event in self.hero.gain_xp(target.xp_reward):
                self.log(event)
            self.log(f"Defeated {target.kind}: +{target.xp_reward} XP.")

    def sword_skill(self, skill: str) -> None:
        if self.hero.skill_cooldown > 0:
            return
        costs = {"linear": 8, "cyclone": 14, "vorpal": 22}
        cost = costs[skill]
        if self.hero.mana < cost:
            self.log("Not enough mana for that sword skill.")
            return
        active = [enemy for enemy in self.enemies if enemy.active]
        target = min(active, key=self.hero.distance_to, default=None)
        if target is None:
            return
        self.hero.mana -= cost
        base = self.hero.attack + self.hero.weapon_level * 4
        if skill == "linear":
            if self.hero.distance_to(target) > 150:
                return
            delta = target.position - self.hero.position
            if delta.length_squared():
                destination = self.hero.position + delta.normalize() * min(95, delta.length())
                if self.world.walkable_pixel(destination.x, destination.y):
                    self.hero.x, self.hero.y = destination
            self.damage_enemy(target, int(base * 1.65))
            self.hero.skill_cooldown = 0.75
            self.log("Linear Flash!")
        elif skill == "cyclone":
            hits = 0
            for enemy in active:
                if self.hero.distance_to(enemy) < 105:
                    self.damage_enemy(enemy, int(base * 1.15))
                    hits += 1
            self.hero.skill_cooldown = 1.15
            self.log(f"Cyclone Arc struck {hits} enemies.")
        else:
            if self.hero.sword_mastery < 50:
                self.hero.mana += cost
                self.log("Vorpal Star unlocks at 50 sword mastery.")
                return
            if self.hero.distance_to(target) > 95:
                self.hero.mana += cost
                return
            self.damage_enemy(target, int(base * 2.8))
            self.hero.skill_cooldown = 1.8
            self.log("Vorpal Star!")
        self.hero.combo = min(5, self.hero.combo + 2)
        self.hero.combo_timer = 1.1
        self.hero.sword_mastery += 3
        for enemy in active:
            if enemy.hp <= 0:
                enemy.defeat()

    def damage_enemy(self, enemy, damage: int) -> None:
        if self.network_client is not None and enemy.floor_boss:
            self.network_client.attack_guardian(damage)
            return
        enemy.hp -= damage

    def sync_network(self) -> None:
        if self.network_client is None:
            return
        self.network_client.set_state(
            x=self.hero.x,
            y=self.hero.y,
            hp=int(self.hero.hp),
            max_hp=int(self.hero.max_hp),
            level=self.hero.level,
        )
        self.apply_network_snapshot()
        if self.network_client.error and not self.network_error_shown:
            self.log(f"Co-op disconnected: {self.network_client.error}")
            self.network_error_shown = True

    def apply_network_snapshot(self) -> None:
        if self.network_client is None:
            return
        snapshot = self.network_client.get_snapshot()
        self.remote_players = [
            player
            for player in snapshot.get("players", [])
            if player.get("id") != self.network_client.player_id
        ]
        guardian = snapshot.get("guardian", {})
        if "hp" in guardian:
            self.floor_guardian.hp = int(guardian["hp"])
            self.floor_guardian.max_hp = int(guardian.get("max_hp", 850))
            self.floor_guardian.active = not bool(guardian.get("cleared", False))

    def player_dodge(self) -> None:
        if self.hero.dodge_cooldown > 0:
            return
        target = min(
            (enemy for enemy in self.enemies if enemy.active),
            key=self.hero.distance_to,
            default=None,
        )
        if not target:
            return
        away = self.hero.position - target.position
        if not away.length_squared():
            away = pygame.Vector2(1, 0)
        candidate = self.hero.position + away.normalize() * 92
        if self.world.walkable_pixel(candidate.x, candidate.y):
            self.hero.x, self.hero.y = candidate
            self.hero.dodge_cooldown = 1.1
            self.hero.hurt_cooldown = 0.35

    def player_spell(self) -> None:
        if self.hero.spell_cooldown > 0 or self.hero.mana < 14:
            return
        target = min(
            (enemy for enemy in self.enemies if enemy.active),
            key=self.hero.distance_to,
            default=None,
        )
        if target is None or self.hero.distance_to(target) > 210:
            return
        self.hero.mana -= 14
        self.hero.spell_cooldown = 0.7
        self.damage_enemy(
            target, int((self.hero.attack + self.hero.weapon_level * 3) * 1.45)
        )
        if target.hp <= 0:
            target.defeat()
            self.hero.kills += 1
            self.hero.quest_kills += 1
            self.hero.gold += target.gold_reward
            if target.chapter == 2:
                self.hero.void_cores += 1
            for event in self.hero.gain_xp(target.xp_reward):
                self.log(event)
            self.log(f"Arcane burst defeated {target.kind}.")

    def hero_death(self) -> None:
        lost = min(self.hero.gold, max(3, self.hero.gold // 5))
        self.hero.gold -= lost
        self.hero.hp = self.hero.max_hp
        self.hero.mana = self.hero.max_mana
        self.hero.x, self.hero.y = self.world.spawn_position()
        self.log(f"You awakened in the village and lost {lost} gold.")

    def draw(self) -> None:
        self.screen.fill(COLORS["night"])
        self.world.draw(self.screen, self.camera)
        for treasure in self.treasures:
            treasure.draw(self.screen, self.camera)
        for enemy in self.enemies:
            if enemy.active:
                enemy.draw(self.screen, self.camera)
        self.draw_remote_players()
        self.echo.draw(self.screen, self.camera)
        self.hero.draw(self.screen, self.camera)
        self.draw_attack_effect()
        self.draw_hud()
        if self.show_player_menu:
            self.draw_player_menu()
        if self.show_progress:
            self.draw_progress_panel()
        pygame.display.flip()

    def draw_remote_players(self) -> None:
        for player in self.remote_players:
            pos = pygame.Vector2(float(player["x"]), float(player["y"])) - self.camera
            color = tuple(player.get("color", [255, 180, 90]))
            pygame.draw.circle(self.screen, color, pos, 16)
            pygame.draw.circle(self.screen, COLORS["white"], pos, 16, 2)
            name = self.small_font.render(
                f"{player.get('name', 'Adventurer')}  Lv.{player.get('level', 1)}",
                True,
                COLORS["white"],
            )
            self.screen.blit(name, name.get_rect(center=(pos.x, pos.y - 29)))

    def draw_attack_effect(self) -> None:
        if 0.26 < self.hero.attack_cooldown < 0.38:
            pos = self.hero.position - self.camera
            pygame.draw.circle(self.screen, COLORS["gold"], pos, 38, 4)
        if self.parry_flash > 0:
            pos = self.hero.position - self.camera
            pygame.draw.circle(self.screen, (99, 242, 255), pos, 48, 5)

    def bar(self, x: int, y: int, width: int, value: float, color, label: str) -> None:
        pygame.draw.rect(
            self.screen, (38, 44, 58), (x, y, width, 16), border_radius=7
        )
        pygame.draw.rect(
            self.screen,
            color,
            (x, y, max(0, int(width * max(0, min(1, value)))), 16),
            border_radius=7,
        )
        text = self.small_font.render(label, True, COLORS["white"])
        self.screen.blit(text, (x + 7, y - 1))

    def draw_hud(self) -> None:
        panel = pygame.Surface((SCREEN_WIDTH, 104), pygame.SRCALPHA)
        panel.fill((*COLORS["panel"], 235))
        self.screen.blit(panel, (0, 0))
        title = self.font.render(
            f"{self.hero.name}  Lv.{self.hero.level}  Floor {self.hero.current_floor}  Combo x{self.hero.combo}",
            True,
            COLORS["white"],
        )
        self.screen.blit(title, (22, 14))
        self.bar(
            22,
            43,
            260,
            self.hero.hp / self.hero.max_hp,
            COLORS["health"],
            f"HP {self.hero.hp}/{self.hero.max_hp}",
        )
        self.bar(
            22,
            66,
            260,
            self.hero.xp / self.hero.xp_next,
            COLORS["xp"],
            f"XP {self.hero.xp}/{self.hero.xp_next}",
        )
        self.bar(
            22,
            87,
            260,
            self.hero.mana / self.hero.max_mana,
            COLORS["mana"],
            f"Mana {int(self.hero.mana)}/{self.hero.max_mana}",
        )
        stats = [
            f"Attack {self.hero.attack} +W{self.hero.weapon_level}",
            f"Gold {self.hero.gold}",
            f"Potions {self.hero.potions}",
            f"Armor rank {self.hero.armor_level}",
            f"Void cores {self.hero.void_cores}",
        ]
        for index, text in enumerate(stats):
            rendered = self.small_font.render(text, True, COLORS["muted"])
            self.screen.blit(rendered, (310 + (index % 3) * 130, 19 + (index // 3) * 28))

        quest_text = self.small_font.render(
            f"Everdawn Online | Floors cleared {self.hero.floors_cleared} | Sword mastery {self.hero.sword_mastery}",
            True,
            COLORS["gold"],
        )
        self.screen.blit(quest_text, (710, 18))
        ai_text = self.small_font.render(
            f"Echo VRMMO mastery {self.echo.vrmmo_mastery()['overall']:.0%} | Party actions {self.echo.party_actions}",
            True,
            COLORS["ai"],
        )
        self.screen.blit(ai_text, (710, 47))
        controls = self.small_font.render(
            "SPACE strike | SHIFT parry | 1-3 sword skills | M menu | P Echo",
            True,
            COLORS["muted"],
        )
        self.screen.blit(controls, (710, 74))
        if self.network_client is not None:
            status = (
                f"ONLINE | Party {len(self.remote_players) + 1}/4"
                if self.network_client.connected
                else "CONNECTING TO CO-OP SERVER..."
            )
            status_image = self.small_font.render(status, True, (116, 235, 155))
            self.screen.blit(status_image, (510, 18))

        if self.floor_guardian.active:
            self.bar(
                355,
                112,
                440,
                self.floor_guardian.hp / self.floor_guardian.max_hp,
                (70, 224, 235),
                f"Floor Guardian: {self.floor_guardian.kind} | Phase {self.floor_guardian.phase}",
            )

        log_panel = pygame.Surface((530, 108), pygame.SRCALPHA)
        log_panel.fill((*COLORS["panel"], 220))
        log_x, log_y = 18, SCREEN_HEIGHT - 126
        self.screen.blit(log_panel, (log_x, log_y))
        for index, message in enumerate(self.messages[-4:]):
            text = self.small_font.render(message[:78], True, COLORS["white"])
            self.screen.blit(text, (log_x + 13, log_y + 12 + index * 23))

        minimap = pygame.Rect(SCREEN_WIDTH - 200, SCREEN_HEIGHT - 150, 182, 132)
        pygame.draw.rect(self.screen, (*COLORS["panel"],), minimap, border_radius=10)
        pygame.draw.rect(self.screen, COLORS["panel_light"], minimap, 2, border_radius=10)
        scale_x = minimap.width / self.world.pixel_width
        scale_y = minimap.height / self.world.pixel_height
        for actor, color, size in [
            (self.hero, COLORS["player"], 5),
            (self.echo, COLORS["ai"], 4),
        ]:
            pygame.draw.circle(
                self.screen,
                color,
                (
                    minimap.x + actor.x * scale_x,
                    minimap.y + actor.y * scale_y,
                ),
                size,
            )

    def draw_progress_panel(self) -> None:
        vrmmo = self.echo.vrmmo_mastery()
        panel = pygame.Surface((570, 425), pygame.SRCALPHA)
        panel.fill((12, 18, 29, 245))
        rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        pygame.draw.rect(panel, COLORS["panel_light"], panel.get_rect(), 2, border_radius=16)
        self.screen.blit(panel, rect)

        title = self.large_font.render(
            f"VRMMO Floor 1 Mastery: {vrmmo['overall']:.0%}", True, COLORS["white"]
        )
        self.screen.blit(title, (rect.x + 32, rect.y + 28))
        subtitle = self.small_font.render(
            (
                "Floor 1 is mastered. Echo is ready for the next floor."
                if vrmmo["overall"] >= 0.85
                else "Echo is learning party combat and the Floor Guardian."
            ),
            True,
            COLORS["ai"],
        )
        self.screen.blit(subtitle, (rect.x + 34, rect.y + 78))

        categories = [
            ("Floor 1 exploration", vrmmo["floor_exploration"], COLORS["xp"]),
            ("Party coordination", vrmmo["party_coordination"], COLORS["mana"]),
            ("Guardian-fight skill", vrmmo["guardian_skill"], COLORS["ai"]),
            ("Floor clears", vrmmo["floor_clears"], COLORS["health"]),
            ("New tactical actions", vrmmo["new_actions"], COLORS["gold"]),
        ]
        for index, (label, value, color) in enumerate(categories):
            y = rect.y + 125 + index * 51
            text = self.font.render(f"{label}  {value:.0%}", True, COLORS["white"])
            self.screen.blit(text, (rect.x + 34, y))
            pygame.draw.rect(
                self.screen,
                COLORS["panel_light"],
                (rect.x + 295, y + 2, 235, 16),
                border_radius=7,
            )
            pygame.draw.rect(
                self.screen,
                color,
                (rect.x + 295, y + 2, int(235 * value), 16),
                border_radius=7,
            )

        hint = self.small_font.render(
            "At 85% mastery, Echo is ready for the next tower floor. Press P to close.",
            True,
            COLORS["muted"],
        )
        self.screen.blit(hint, (rect.x + 34, rect.bottom - 42))

    def draw_player_menu(self) -> None:
        panel = pygame.Surface((620, 470), pygame.SRCALPHA)
        panel.fill((9, 20, 31, 247))
        rect = panel.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        pygame.draw.rect(panel, (77, 213, 232), panel.get_rect(), 2, border_radius=18)
        self.screen.blit(panel, rect)
        title = self.large_font.render("PLAYER STATUS", True, (116, 232, 255))
        self.screen.blit(title, (rect.x + 36, rect.y + 28))
        rows = [
            ("Player", self.hero.name),
            ("Current floor", str(self.hero.current_floor)),
            ("Floors cleared", str(self.hero.floors_cleared)),
            ("Level", str(self.hero.level)),
            ("Sword mastery", str(self.hero.sword_mastery)),
            ("Weapon", f"Voidblade +{self.hero.weapon_level}"),
            ("Armor", f"Night Armor +{self.hero.armor_level}"),
            ("Attack", str(self.hero.attack)),
            ("Gold", str(self.hero.gold)),
            ("Party member", "Echo [Learning AI]"),
        ]
        for index, (label, value) in enumerate(rows):
            y = rect.y + 100 + index * 29
            self.screen.blit(self.font.render(label, True, COLORS["muted"]), (rect.x + 42, y))
            value_image = self.font.render(value, True, COLORS["white"])
            self.screen.blit(value_image, (rect.right - 42 - value_image.get_width(), y))
        footer = self.small_font.render(
            "Skills: [1] Linear Flash  [2] Cyclone Arc  [3] Vorpal Star  |  M to close",
            True,
            (116, 232, 255),
        )
        self.screen.blit(footer, (rect.x + 42, rect.bottom - 42))

    def save(self) -> None:
        data = {
            field: getattr(self.hero, field)
            for field in (
                "x",
                "y",
                "level",
                "xp",
                "xp_next",
                "max_hp",
                "hp",
                "max_mana",
                "mana",
                "attack",
                "gold",
                "potions",
                "soul_shards",
                "rebirths",
                "legacy_power",
                "kills",
                "quest_kills",
                "quest_target",
                "weapon_level",
                "armor_level",
                "void_cores",
                "boss_kills",
                "current_floor",
                "floors_cleared",
                "sword_mastery",
            )
        }
        (ROOT / "savegame.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        self.echo.save()

    def load(self) -> None:
        path = ROOT / "savegame.json"
        if not path.exists():
            self.log("No saved world exists yet.")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(self.hero, key):
                    setattr(self.hero, key, value)
            self.log("Saved world loaded.")
        except (OSError, ValueError, TypeError):
            self.log("The save file could not be loaded.")

    def run(self, max_frames: int | None = None) -> None:
        frames = 0
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            self.handle_events()
            self.update(dt)
            self.draw()
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        self.echo.save()
        if self.network_client is not None:
            self.network_client.close()
        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Everdawn Online: Ascension")
    parser.add_argument("--online", action="store_true", help="Connect to a co-op server")
    parser.add_argument("--host", default="127.0.0.1", help="Co-op server address")
    parser.add_argument("--port", type=int, default=7777)
    parser.add_argument("--name", default="Ari")
    args = parser.parse_args()

    client = None
    if args.online:
        from network_client import CoopClient

        client = CoopClient(args.host, args.port, args.name)
        client.start()
    Game(network_client=client, player_name=args.name).run()
