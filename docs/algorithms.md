# Handover Algorithms

This document describes the four handover algorithms implemented in the simulator. All algorithms share the same input (ns-3 traces loaded as `simDataframes[ue][gnb]`) and produce a per-algorithm `results.csv` file.

---

## 1. 3GPP Rel.15 A3 Event-Triggered Handover

**Module:** `simulator_3gpp.py`  
**Results folder:** `results/3GPP_A3/`

### Description

Implements the standard handover procedure defined in 3GPP TS 36.331 / TS 38.331, based on the **A3 measurement event**: a handover is prepared when a neighbouring cell's signal becomes stronger than the serving cell by more than a configurable margin, and that condition holds for the Time-To-Trigger (TTT) duration.

### Decision rule

An A3 event fires when:

$$\text{RSRP}_\text{neighbour} - \text{RSRP}_\text{serving} > \text{Hys} + \text{A3Offset}$$

The event must remain true for the entire TTT window before a handover is executed.

### Key parameters

| Parameter | CLI flag | Default | Description |
|-----------|----------|---------|-------------|
| Hysteresis | `--Hys` | `5.0 dBm` | Prevents ping-pong handovers |
| A3 Offset | `--A3Offset` | `3.0 dBm` | Additional offset applied to the event condition |
| Time-To-Trigger | `--ttt` | `0.1 s` | Duration the condition must hold before triggering |
| Measurement interval | `--NrMeasureInt` | `0.1 s` | How often the RSRP is evaluated |
| Handover interval | `--HOInterval` | `0.1 s` | Minimum time between consecutive handovers |

### Handover penalty

After each handover, a short service interruption is modelled by degrading the `Latency` column of the new serving cell by `penalty_dict["Latency"]` (default 20 ms) for one `penalty_time` period.

---

## 2. 3GPP Rel.16 Conditional Handover (CHO)

**Module:** `simulator_3gpp_rel16.py`  
**Results folder:** `results/3GPP_CHO/`

### Description

Implements the **Conditional Handover** mechanism introduced in 3GPP Release 16. In CHO, the UE prepares a set of candidate cells in advance (handover command is buffered), and the actual handover execution is triggered only when a radio condition is satisfied — decoupling preparation from execution.

This reduces handover interruption time because the UE does not need to wait for an explicit command from the source base station when conditions deteriorate rapidly (e.g., at cell edge).

### Differences from Rel.15 A3

| Aspect | 3GPP Rel.15 | 3GPP Rel.16 CHO |
|--------|------------|-----------------|
| Preparation | On trigger | Proactive (ahead of time) |
| Execution | Immediately after trigger | When execution condition is met |
| Robustness to sudden signal drops | Lower | Higher |

### Parameters

Shares the same hysteresis, A3 offset, TTT, and penalty parameters as Rel.15. The CHO execution condition is evaluated against the candidate cell set prepared during the preparation phase.

---

## 3. Score-Based Greedy Handover (SBGH)

**Module:** `simulator_sbgh.py`  
**Results folder:** `results/SBGH/` and `results/ideal-SBGH/`

### Description

A proposed heuristic algorithm that continuously evaluates a **score** for each candidate cell and connects the UE to the highest-scoring cell. The score incorporates both signal quality (RSRP) and cell capabilities (bandwidth, carrier frequency), going beyond raw signal strength used by the 3GPP A3 event.

### Scoring function

Defined in `scoring.py`:

$$\text{score} = \alpha \cdot \frac{\text{BW}_\text{user}}{\text{BW}_\text{max}} \cdot p(\text{RSRP})$$

where:

- $\text{BW}_\text{user}$ — user-allocated bandwidth for the candidate gNB's band (Hz)
- $\text{BW}_\text{max} = 400\,\text{MHz}$ — normalisation constant
- $p(\text{RSRP})$ — normalised signal quality:

$$p = \frac{\text{RSRP} - \text{RSRP}_{\min}}{\text{RSRP}_{\max} - \text{RSRP}_{\min}}, \quad \text{clamped to } [0, 1]$$

with $\text{RSRP}_{\min} = -100$ and $\text{RSRP}_{\max} = -80$.

- $\alpha$ — tunable weight (CLI: `--alpha`, default `5000.0`)

### Decision threshold

A handover is only executed if:

$$\frac{\text{score}_{\text{best}}}{\text{score}_{\text{current}}} > 1.25$$

This avoids unnecessary handovers to marginally better cells.

### Variants

| Variant | Delay | Folder |
|---------|-------|--------|
| `ideal-SBGH` | 0 intervals (instantaneous) | `results/ideal-SBGH/` |
| `SBGH` | `DELAY_INTERVALS = 1` interval | `results/SBGH/` |

The ideal variant serves as an upper-bound benchmark.

---

## 4. Multi-Agent Double Deep Q-Network (MA-DDQN)

**Module:** `simulator_gti_dqn.py`  
**Agent:** `dqn.py` — `DQNAgent` class  
**Environment:** `environment.py` — `Environment` class  
**Results folder:** `results/DDQN/`

### Description

A reinforcement learning approach where each UE is controlled by an independent `DQNAgent`. The agent learns a policy mapping radio observations to gNB selection decisions, optimising long-term cumulative throughput while minimising handover cost.

It uses a **Double DQN** architecture (separate policy and target networks) to reduce overestimation of Q-values.

### State space

At each decision step the agent observes, for every gNB:

- RSRP
- Instantaneous throughput
- gNB bandwidth occupation level

### Action space

Discrete: select one of the $N_\text{gNB}$ available gNodeBs.

### Reward

Derived from the throughput received after taking the action, minus any handover penalty incurred.

### Neural network

```
Input  → Dense(32, ReLU) → Dense(32, ReLU) → Dense(nGnbs, linear)
Loss: Huber loss (δ = 1.0)
Optimizer: Adam
```

### Training hyperparameters

| Hyperparameter | Value |
|----------------|-------|
| Discount factor γ | 0.9 |
| Replay memory size | 500 |
| Batch size | variable |
| Initial ε (exploration) | 0.9 |
| Min ε | 0.01 |
| ε decay | 0.995 per replay step |
| Target network sync rate | every 10 replay steps |
| Learning rate | 0.01 |

### Training loop

1. At each time step the agent observes the environment state.
2. With probability ε it chooses a random gNB (exploration); otherwise it picks $\arg\max_a Q(s, a; \theta)$ (exploitation).
3. The experience $(s, a, r, s', \text{done})$ is stored in the replay buffer.
4. After accumulating sufficient experience, a minibatch is sampled and the policy network is updated using the DDQN target:

$$y = r + \gamma \cdot Q(s', \arg\max_{a'} Q(s', a'; \theta); \theta^-)$$

1. Every `sync_rate` steps the target network weights $\theta^-$ are copied from the policy network.
