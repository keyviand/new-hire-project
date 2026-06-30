# Echo Machine Learning Guide

Echo uses **tabular Q-learning**, an inspectable reinforcement-learning algorithm. It does not use a neural network. That is intentional: the complete decision table can be viewed, tested, saved, and debugged.

## The control loop

Every 0.35 seconds the server performs this sequence:

1. Convert the current world into a small state.
2. List actions that are valid in that state.
3. Update the previous state/action Q-value using the reward just received.
4. Choose the next action with an epsilon-greedy policy.
5. Execute that action while collecting the next reward.

The browser only visualizes the result. Learning and authoritative gameplay happen on the server.

## State representation

An example state is:

```text
hp=hurt|energy=ready|range=close|threat=elite|ally=yes
```

Echo discretizes continuous values into categories:

- Health: `healthy`, `hurt`, or `critical`
- Energy: `ready` or `low`
- Enemy range: `none`, `far`, `near`, or `close`
- Threat: `none`, `normal`, `elite`, or `unique`
- Ally nearby: `yes` or `no`

This is called **feature engineering** and **state discretization**. A small state space learns quickly and is easy to inspect, although it loses some detail.

## Actions

- `approach`: move toward the selected enemy
- `strike`: balanced damage and risk
- `circle`: lower damage with much lower counter-damage
- `power`: high damage, high risk, and energy cost
- `retreat`: create distance and recover slowly
- `explore`: travel toward new world locations
- `support`: move toward a player, recover, and earn support reward
- `patrol`: move around the safe area when no enemy is active

Valid-action filtering prevents impossible actions such as striking an enemy on the other side of the map.

## Reward function

The reward is deliberately composed from several signals:

| Event | Reward |
|---|---:|
| Damage dealt | `+0.045` per HP |
| Normal kill | `+7` |
| Elite kill | `+10` |
| Unique kill | `+15` |
| Boss damage | `+0.06` per HP |
| Discover a map tile | `+0.4` |
| Stay near a player | small positive reward over time |
| Take damage | `-0.07` per HP |
| Movement action gets stuck | `-0.45` |
| Death | `-20` |

Reward design is part of the product specification. If a reward is too large, Echo may exploit it and ignore the intended game. If every reward is delayed, learning becomes slow because the agent cannot tell which earlier action caused the outcome.

## Q-learning equation

```text
new_Q = old_Q + alpha * (reward + gamma * best_future_Q - old_Q)
```

- `alpha` is the learning rate (`0.18`). It controls how quickly new evidence replaces old knowledge.
- `gamma` is the future discount (`0.92`). It makes future rewards valuable, but slightly less valuable than immediate rewards.
- `best_future_Q` is the best value Echo currently knows for the next state.

The expression inside parentheses is the **temporal-difference error**: the difference between what Echo expected and what actually happened plus what it now expects next.

## Exploration versus exploitation

Echo uses an epsilon-greedy policy:

- With probability epsilon, choose a random valid action and gather new evidence.
- Otherwise, choose an action with the highest known Q-value.

Epsilon begins at `0.28`, decays after each decision, and never falls below `0.05`. Keeping a small minimum allows Echo to adapt if the game changes later.

## Persistence

The learned Q-table and training statistics are saved in `echo_brain_q.json`. That runtime file is intentionally excluded from Git because it belongs to the running server, not the source code.

## Debugging workflow

Press `P` in the browser and inspect:

1. **State**: Did the feature encoder describe the situation correctly?
2. **Valid/chosen action**: Was the action possible and sensible?
3. **Last reward**: Did the sign and magnitude match the outcome?
4. **Q-values**: Which action does Echo expect to be best, and by how much?
5. **Epsilon**: Was the surprising action intentional exploration?
6. **Q-value change**: Is learning happening, exploding, or remaining zero?
7. **Action counts**: Is one action dominating unexpectedly?

When behavior is wrong, debug in that order. Do not immediately tune the model. Many apparent “AI problems” are state bugs, invalid action masks, reward-sign mistakes, stale data, or persistence problems.

## Current limitations

- States use broad categories and do not encode obstacles or several simultaneous enemies.
- Q-learning treats each encoded state as unrelated; it cannot generalize from one state to a similar unseen state.
- Echo learns continuously in the shared live world, so other players change its training environment.
- Reward weights are initial design choices and will need observation and tuning.

A later neural-network policy could generalize across continuous inputs, but it would also be harder to explain and debug. This tabular version establishes a trustworthy baseline first.
