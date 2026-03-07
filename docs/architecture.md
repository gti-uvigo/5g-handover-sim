# System Architecture

## Overview

The simulator is composed of two loosely-coupled layers that communicate through CSV trace files. This split decouples the computationally expensive physical-layer simulation (handled by ns-3) from the algorithmic handover evaluation (handled in Python), making it easy to:

- Run the ns-3 simulations once and evaluate many handover strategies without repeating the expensive physical simulation.
- Replace either layer independently.

---

## Layer 1 – Network Simulator (C++ / ns-3 + 5G-LENA)

**Location:** `network-simulator/`

### Purpose

Simulates the low-level 5G NR radio access network. For each UE and each gNodeB in the scenario, a dedicated ns-3 simulation run is launched. Every run records the radio channel metrics as seen from a single UE towards a single gNB.

### Key parameters passed at run time

| ns-3 argument | Description |
|---------------|-------------|
| `--path` | Output folder for the trace CSV |
| `--simTime` | Simulation duration (seconds) |
| `--gnb` | Target gNB index for this run |
| `--sc` | Path to the scenario definition file |
| `--seed` | Per-node RNG seed |
| `--int` | Trace sampling interval (microseconds) |
| `--errorModel` | PHY error model (e.g., `ns3::NrEesmCcT1`) |
| `--speed` | UE speed (m/s) |
| `--wp` | Path to waypoints file (optional) |

### Output

A CSV file at `traces/<run>/<ue>/<gnb>/traces.csv` with one row per sampling interval containing:

| Column | Description |
|--------|-------------|
| `Time` | Simulation time (seconds) |
| `Rsrp` | Reference Signal Received Power (RSRP index) |
| `Throughput` | Instantaneous RX throughput (bits/s) |
| `TxPackets` | Cumulative transmitted packets |
| `TxBytes` | Cumulative transmitted bytes |
| `RxPackets` | Cumulative received packets |
| `RxBytes` | Cumulative received bytes |
| `LostPackets` | Cumulative lost packets |
| `Latency` | Per-packet latency |

### Parallelism

The Python orchestrator launches one ns-3 process per UE–gNB pair in a `ThreadPoolExecutor` using all available CPU cores (`nUEs × nGnbs` simultaneous processes).

---

## Layer 2 – Handover Simulator (Python)

**Location:** `handover-simulator/src/`

### Purpose

Reads the ns-3 traces and replays them through each handover algorithm. No new ns-3 simulation is needed; the algorithms make decisions based only on the pre-recorded trace data.

### Entry point

`main.py` orchestrates the entire workflow:

1. **Parse arguments** (CLI or YAML config file).
2. **Parse scenario** from `sc.txt` → `scenario` dict.
3. **Launch ns-3 simulations** (unless `--trace` is provided).
4. **Load traces** into a `simDataframes[ue][gnb]` nested list.
5. **Compute derived columns** (`Throughput`, `*Diff` columns).
6. **Run all four algorithms** in sequence, writing results to `results/<algorithm>/results.csv`.

### Module roles

| Module | Role |
|--------|------|
| `utils.py` | CSV loading, datarate helpers, penalty application |
| `simulator_common.py` | Channel simulation, shared replay logic |
| `scoring.py` | SBGH scoring function |
| `occupation.py` | gNB load / bandwidth occupation calculation |
| `nrEvents.py` | NR A3 event state machine (hysteresis + TTT) |
| `environment.py` | OpenAI Gym-style environment for DDQN training |
| `dqn.py` | `DQNAgent` class (DDQN, experience replay, target network) |
| `simulator_3gpp.py` | 3GPP Rel.15 A3 algorithm |
| `simulator_3gpp_rel16.py` | 3GPP Rel.16 CHO algorithm |
| `simulator_sbgh.py` | SBGH and ideal-SBGH algorithms |
| `simulator_gti_dqn.py` | Multi-agent DDQN algorithm |

---

## Data Flow

1. `main.py` parses `sc.txt` and `wp.txt`, then spawns one ns-3 process per UE–gNB pair.
2. Each ns-3 process writes its results to `traces/<run>/<ue>/<gnb>/traces.csv`.
3. Once all ns-3 runs finish, `main.py` loads all CSVs into the `simDataframes[ue][gnb]` structure.
4. The four handover algorithms (3GPP A3, CHO, SBGH, MA-DDQN) are run sequentially on the loaded data.
5. Each algorithm writes its output to `results/<algorithm>/results.csv`.

---

## Trace Folder Structure

```
traces/
└── 2025-01-15_10-30-00/          ← timestamped run
    ├── parameters.json           ← parameters snapshot
    ├── 0/                        ← UE 0
    │   ├── 0/traces.csv          ← UE 0 vs gNB 0
    │   ├── 1/traces.csv          ← UE 0 vs gNB 1
    │   └── ...
    ├── 1/                        ← UE 1
    │   └── ...
    └── results/
        ├── 3GPP_A3/results.csv
        ├── 3GPP_CHO/results.csv
        ├── SBGH/results.csv
        ├── ideal-SBGH/results.csv
        └── DDQN/results.csv
```
