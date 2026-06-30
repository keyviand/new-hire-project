# Everdawn Online: Ascension

Echo now uses persistent tabular Q-learning. See [ECHO_MACHINE_LEARNING.md](ECHO_MACHINE_LEARNING.md) for the state design, actions, rewards, equation, and debugging workflow.

A local 2D open-world fantasy RPG prototype written in Python and Pygame.

This is an original VRMMO-style world. It does not copy characters, locations,
story, music, or artwork from existing anime.

## VRMMO Ascension update

- Skyglass Fields as the first tower floor
- Protected village and portal safe zones with rapid recovery
- Asterion, the three-phase Floor 1 Guardian
- Defeating Asterion unlocks Floor 2 at the cyan ascent portal
- Five-hit basic sword combos
- Short perfect-parry windows
- Three sword skills with mana costs and cooldowns
- Player status and equipment menu
- Echo party guarding and synchronized guardian attacks
- A fresh VRMMO Floor 1 mastery curriculum

## Included now

- Large scrolling world with a village, roads, forests, water, and encounter zones
- Real-time movement and combat
- Monsters with pursuit and wandering behavior
- Chasers, ranged wisps, and heavily armored Ash Wardens
- Experience, levels, health, attack, gold, potions, and quests
- Treasure chests and potion caches spread across the world
- Arcane ranged attacks and tactical dodging
- Elite enemies that drop soul shards
- Reincarnation at level 5 with permanent legacy power
- Save and load support
- Echo, an AI adventurer that learns with reinforcement learning
- Separate fast AI-training mode

## Chapter 2: The Ashen Reach

- A corrupted eastern biome connected to the original open world
- The Obsidian Vault dungeon in the southeast
- Void Stalkers, ranged Cinder Mages, and armored Hollow Knights
- The Hollow Sovereign boss with three increasingly aggressive phases
- Void cores dropped by Chapter 2 enemies
- A village forge marked `F` that upgrades weapons and armor
- A fresh Chapter 2 mastery curriculum for Echo

All visuals are drawn by the game code. No API or online AI service is used.

## Start playing

Run:

```powershell
.\start_game.ps1
```

## Online co-op (2-4 players)

The host starts the authoritative server by double-clicking:

```text
start_coop_server.bat
```

On the same computer, double-click `join_local_coop.bat`. Other players on the
same private network run:

```powershell
.\.venv\Scripts\python.exe game.py --online --host HOST_IP --port 7777 --name PlayerName
```

Replace `HOST_IP` with the host computer's local IPv4 address. Windows Firewall
may ask the host to allow Python on private networks.

The co-op server validates player speed, world bounds, Guardian attack range,
attack rate, and maximum damage. Player movement and the Floor Guardian fight
are shared.

For internet play, use a trusted private gaming VPN or carefully forward TCP
port 7777. This prototype does not yet provide accounts, encryption, moderation,
or denial-of-service protection, so do not expose it as a public MMO server.

## Browser version

Double-click `start_browser_game.bat`. On the host computer, open:

```text
http://127.0.0.1:8000
```

Friends on the same network open `http://HOST_IP:8000`. They only need a modern
web browser; they do not install Python or the game. The host may need to allow
Python through Windows Firewall on private networks for TCP port 8000.

The browser world includes shared Slimes, Fanglings, Wisps, Ash Wardens, Hollow
Knights, Cinder Mages, and Void Stalkers. Monsters chase and damage players on
the server, respawn after defeat, grant XP and levels, and drop shared gold or
healing. Echo is also server-controlled, so every connected player sees the
same AI companion and battles.

Players receive repeatable hunt quests that grow after each completion and
award bonus XP and gold. Press `E` in the browser to spend 15 Mana on Ascension
Burst, an area sword skill that damages nearby monsters and Floor Guardians.
Press `P` to view Echo's live mastery dashboard: exploration, monster knowledge,
combat skill, boss training, party support, and overall readiness for new
content. At 85% overall mastery, the dashboard recommends adding more systems.

The browser renderer includes the offline game's major visual regions: village
buildings, paths, grass, forests, water, rocks, Skyglass crystals, corrupted
ground, dungeon tiles, portals, swords, monster silhouettes, health bars, and
loot effects. Floor Guardians progress automatically: Asterion is followed by
Nyxara and then Orinox after an eight-second ascent countdown. Later cycles
repeat with increased health.

To turn this into a public HTTPS URL, deploy the `browser` folder and
`browser_server.py` behind a host or reverse proxy that supports WebSockets and
TLS. HTTP and WebSockets now share port 8000, making one-URL tunnels possible.
Configure the page with `?ws=wss://YOUR-SERVER/websocket` only when the public
WebSocket URL differs from `/ws`. Public deployment still needs accounts,
rate limiting, persistent storage, monitoring, and moderation before it should
be treated as an open MMO service.

### Temporary public link

Double-click `start_public_game.bat`. One supervisor window starts both the game
server and Cloudflare Quick Tunnel, automatically chooses a free local port,
and prints the `https://...trycloudflare.com` URL. It also saves the latest URL
in `PUBLIC_LINK.txt`. Send that URL to your friend and keep the supervisor
window open. The address changes whenever the tunnel restarts and is intended
only for testing with people you trust.

Controls:

- `W A S D`: move
- `Space`: attack the nearest enemy
- `Shift`: attempt a perfect parry
- `1`: Linear Flash dash attack
- `2`: Cyclone Arc area attack
- `3`: Vorpal Star heavy skill (requires 50 sword mastery)
- `M`: open the player status and equipment menu
- `E`: cast an arcane burst at a nearby enemy
- `Q`: dodge away from the nearest enemy
- `F`: interact with the gold quest marker
- `F`: also use the orange forge marker to spend void cores
- `H`: drink a healing potion
- `R`: reincarnate while standing near the violet shrine
- `F5`: save
- `F9`: load
- `T`: manually return Echo to the village
- `P`: open Echo's detailed learning-progress screen
- `Esc`: quit

## Train the AI companion

Echo learns while the game is running. To give it many experiences quickly:

```powershell
.\.venv\Scripts\python.exe train_ai.py --steps 100000
```

Its learned Q-values are saved in `ai_brain_vrmmo.json` and loaded next time the game
starts. Echo now observes health, enemy direction and strength, nearby danger,
terrain obstacles, potion supply, and treasure. It can explore, pursue treasure,
choose quick or heavy attacks, dodge, heal, rest, and learn survival tactics.

Echo also has a safety watchdog. If it remains trapped against terrain for about
nine seconds, repeatedly fails to move, or enters an invalid tile, it
automatically returns to the village and learns a penalty from the incident.

## Echo mastery percentage

The HUD shows Echo's overall mastery. Press `P` for the full breakdown:

- World exploration
- Situation knowledge
- Tactical-action practice
- Combat experience
- Treasure seeking

The progress panel now tracks VRMMO Floor 1 separately: floor exploration,
party coordination, Guardian-fight skill, floor clears, and the two new party
actions. At 85%, Echo is ready for the next tower floor.

## Current scope

This is the first playable vertical slice, not yet a complete commercial RPG.
It establishes the systems we can grow: maps, story, dialogue, inventory,
abilities, dungeons, procedural quests, and richer learning agents.
