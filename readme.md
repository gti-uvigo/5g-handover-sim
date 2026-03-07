# End-to-end Handover Simulator for 5G Heterogeneous Network Environments

[![DOI_CODE](https://zenodo.org/badge/DOI/10.5281/zenodo.15772613.svg)](https://doi.org/10.5281/zenodo.15772613)
[![DOI_PAPER](https://img.shields.io/badge/DOI-10.1109%2FOJCOMS.2025.3649168-green)](https://doi.org/10.1109/OJCOMS.2025.3649168)
[![Docker Image CI](https://github.com/gti-uvigo/5g-handover-sim/actions/workflows/docker-image.yml/badge.svg)](https://github.com/gti-uvigo/5g-handover-sim/actions/workflows/docker-image.yml)
[![Github Pages CI](https://github.com/gti-uvigo/5g-handover-sim/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/gti-uvigo/5g-handover-sim/actions/workflows/pages/pages-build-deployment)

# Introduction

This repository contains a full-stack 5G HetNet Simulator designed to evaluate the performance of various handover algorithms in heterogeneous network environments. The simulator couples:

- A **network-level simulator** built on [ns-3 3.41](https://www.nsnam.org/) with the [5G-LENA](https://5g-lena.cttc.es/) module, which generates realistic PHY/MAC traces for each UE–gNB pair.
- A **high-level handover simulator** written in Python that consumes those traces and runs different handover decision algorithms.

This architecture lets you run full-stack experiments — from radio propagation to AI-based handover decisions — without modifying the ns-3 core.

**Tested with:**
- ns-3 3.41
- 5G-LENA 3.x.y

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Handover Algorithms](#handover-algorithms)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Simulator](#running-the-simulator)
- [Configuration Reference](#configuration-reference)
- [Scenario & Waypoints Files](#scenario--waypoints-files)
- [Output Format](#output-format)
- [Documentation](#documentation)
- [License](#license)
- [Citation](#citation)

---

## Architecture Overview

The simulator has two layers:

1. **Network simulator** (`network-simulator/sim.cc`, C++/ns-3 + 5G-LENA) — runs one simulation per UE–gNB pair and writes the results as CSV traces.
2. **Handover simulator** (`handover-simulator/src/main.py`, Python) — reads those traces and evaluates the four handover algorithms, producing per-algorithm `results.csv` files.

See [docs/architecture.md](docs/architecture.md) for a detailed description of the data flow.

---

## Handover Algorithms

| # | Algorithm | Module | Description |
|---|-----------|--------|-------------|
| 1 | **3GPP Rel.15 A3** | `simulator_3gpp.py` | Standard A3 event-triggered handover with configurable hysteresis and Time-To-Trigger (TTT). |
| 2 | **3GPP Rel.16 CHO** | `simulator_3gpp_rel16.py` | Conditional Handover — preparation and execution are decoupled; execution occurs only when a condition is met. |
| 3 | **Score-Based Greedy Handover (SBGH)** | `simulator_sbgh.py` | Proposed heuristic that scores candidate cells using RSRP, bandwidth, and carrier frequency, then greedily selects the best cell. Includes an *ideal* (zero-delay) variant. |
| 4 | **Multi-Agent DDQN** | `simulator_gti_dqn.py` | Multi-agent Double Deep Q-Network that learns an optimal per-UE handover policy via experience replay. |

> SBGH and the Multi-Agent DDQN are described in the associated publication — see [Citation](#citation).

See [docs/algorithms.md](docs/algorithms.md) for full algorithm details.

---

## Project Structure

```
5g-handover-sim/
├── dockerfile                        # Docker build file
├── docker-compose.yml                # Docker Compose service definition
├── requirements.txt                  # Python dependencies (used by Docker)
├── docs/                             # Extended documentation
│   ├── architecture.md
│   ├── algorithms.md
│   ├── configuration.md
│   └── scenario-format.md
├── network-simulator/                # ns-3 C++ simulation module
│   ├── sim.cc                        # Main simulation entry point
│   ├── sim.h
│   └── LICENSE                       # GPL-2.0
└── handover-simulator/               # Python high-level simulator
    ├── requirements.txt
    ├── scenario/
    │   └── sc.txt                    # Default scenario definition
    ├── waypoints/
    │   └── wp.txt                    # Default UE mobility waypoints
    └── src/
        ├── main.py                   # Entry point & CLI
        ├── environment.py            # DDQN environment abstraction
        ├── dqn.py                    # DQNAgent (DDQN implementation)
        ├── simulator_3gpp.py         # 3GPP Rel.15 algorithm
        ├── simulator_3gpp_rel16.py   # 3GPP Rel.16 CHO algorithm
        ├── simulator_sbgh.py         # SBGH algorithm
        ├── simulator_gti_dqn.py      # Multi-agent DDQN algorithm
        ├── simulator_common.py       # Shared simulation utilities
        ├── scoring.py                # SBGH scoring functions
        ├── occupation.py             # gNB load helpers
        ├── nrEvents.py               # NR measurement event helpers
        ├── utils.py                  # General utilities & data loaders
        └── logging.conf              # Logging configuration
```

---

## Prerequisites

### Docker (recommended)

- [Docker Engine](https://docs.docker.com/engine/install/) ≥ 20.10
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.0

### Native

- Ubuntu 22.04 (recommended)
- ns-3 3.41 with 5G-LENA 3.x.y — see the [5G-LENA getting-started guide](https://cttc-lena.gitlab.io/nr/html/index.html#getting-started)
- Python 3.10+

---

## Installation

### Option A – Docker (recommended)

The Docker image automatically installs ns-3.41, 5G-LENA, and all Python dependencies.

**1. Verify Docker is running:**
```bash
sudo systemctl status docker.service
sudo systemctl status docker.socket
```

**2. (Optional) Add your user to the `docker` group to avoid `sudo`:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**3. Build and start the container:**
```bash
docker compose up -d --build
```

**4. Open an interactive shell inside the container:**
```bash
docker compose run simulator
```

**5. Continue to [Running the Simulator](#running-the-simulator).**

---

### Option B – Native

**1. Set up ns-3 and 5G-LENA** following the [official guide](https://cttc-lena.gitlab.io/nr/html/index.html#getting-started). Install ns-3 in the `ns-3-dev` directory at the root of this repository.

**2. Create the symbolic link for the network simulator:**
```bash
ln -s /absolute/path/to/network-simulator /absolute/path/to/ns-3-dev/scratch/network-simulator
```

**3. Install Python dependencies:**
```bash
pip3 install -r requirements.txt
```

---

## Running the Simulator

### 1. Build ns-3 (optimized profile)

```bash
cd ns-3-dev
./ns3 configure --build-profile=optimized
./ns3 build
```

### 2. Navigate to the handover simulator

```bash
cd ../handover-simulator/src
```

### 3. Run the simulator

```bash
python3 main.py
```

To see all available options:

```bash
python3 main.py --help
```

### 4. Re-use existing traces (skip ns-3)

```bash
python3 main.py --trace /path/to/traces/<run-folder>
```

### 5. Use a YAML configuration file

```bash
python3 main.py --config my_config.yaml
```

---

## Configuration Reference

| Argument | Default | Description |
|----------|---------|-------------|
| `--simTime` | `10.0` | Simulation duration in seconds (0 = derive from waypoints) |
| `--nUEs` | `5` | Number of User Equipment nodes |
| `--seed` | `1234` | Random number generator seed |
| `--speed` | `10.0` | UE speed in m/s |
| `--trayectoryTime` | `5.0` | Trajectory segment duration in seconds |
| `--int` | `0.1` | Sampling interval in seconds |
| `--sc` | `../../handover-simulator/scenario/sc.txt` | Scenario definition file |
| `--wp` | `../../handover-simulator/waypoints/wp.txt` | Waypoints file |
| `--trace` | *(none)* | Path to existing trace folder (skips ns-3) |
| `--config` | *(none)* | Path to a YAML configuration file |
| `--Hys` | `5.0` | A3 event hysteresis in dBm |
| `--A3Offset` | `3.0` | A3 event offset in dBm |
| `--ttt` | `0.1` | Time-To-Trigger in seconds |
| `--NrMeasureInt` | `0.1` | NR measurement interval in seconds |
| `--HOInterval` | `0.1` | Handover evaluation interval in seconds |
| `--alpha` | `5000.0` | SBGH scoring weight for bandwidth/RSRP |
| `--beta` | `1000.0` | SBGH secondary scoring parameter |
| `--packetSize` | `1000` | UDP packet size in bytes |
| `--bitRate` | `380000000` | UDP traffic bitrate in bits/s |
| `--MaxPackets` | `0` | Max packets per flow (0 = unlimited) |
| `--errorModel` | `ns3::NrEesmCcT1` | ns-3 error model |
| `--tolerance` | `1.0` | Mobility position tolerance in meters |
| `--logging` | `0` | Enable ns-3 component logging (1 = on) |

See [docs/configuration.md](docs/configuration.md) for full details and examples.

---

## Scenario & Waypoints Files

### Scenario file (`sc.txt`)

Defines the simulation area, frequency bands, and gNodeB placement.

```
# Scenario dimensions  (MinX MaxX MinY MaxY)
!-400 400 -200 200

# Bands  (* Band_ID  Central_Freq_Hz  User_BW_Hz  GNB_BW_Hz)
*0 3.5e9 20e6 400e6
*1 28e9 100e6 400e6

# gNodeBs  (ID  X  Y  Z  Band_ID  Tx_Power_dBm  Type[I|H])
0 -200.0 50.0 3.0 1 23.0 I   # Micro isotropic (mmWave)
6  0.0  150.0 20.0 0 53.0 H  # Macro hexagonal (sub-6 GHz)
```

See [docs/scenario-format.md](docs/scenario-format.md) for the full file format reference, including the waypoints file syntax.

---

## Output Format

Each run produces a timestamped folder under `handover-simulator/src/traces/`:

```
traces/<YYYY-MM-DD_HH-MM-SS>/
├── parameters.json              # Simulation parameters snapshot
├── <ue>/<gnb>/traces.csv        # Raw ns-3 traces per UE–gNB pair
└── results/
    ├── 3GPP_A3/results.csv
    ├── 3GPP_CHO/results.csv
    ├── SBGH/results.csv
    ├── ideal-SBGH/results.csv
    └── DDQN/results.csv
```

Each `results.csv` contains per-interval metrics: throughput, handover count, packet loss, and accumulated bytes.

---

## Documentation

Extended documentation is in the [`docs/`](docs/) folder:

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System architecture and data flow |
| [docs/algorithms.md](docs/algorithms.md) | Detailed description of each handover algorithm |
| [docs/configuration.md](docs/configuration.md) | Full CLI and YAML configuration reference |
| [docs/scenario-format.md](docs/scenario-format.md) | Scenario and waypoints file format specification |

---

## License

This repository contains two components, each under a different license:

- The **handover simulator** (`handover-simulator/`) is distributed under the **MIT License**. The DDQN agent code is based on [PacktPublishing/Advanced-Deep-Learning-with-Keras](https://github.com/PacktPublishing/Advanced-Deep-Learning-with-Keras).
- The **network simulator** (`network-simulator/`) is distributed under the **GNU General Public License v2 (GPL-2.0)**. It is based on code examples from [5G-LENA](https://5g-lena.cttc.es/).

---

## Citation

If you use this code in your research, please cite:

```bibtex
@ARTICLE{rua2026intelligent,
  author={Rúa-Estévez, José Manuel and Fondo-Ferreiro, Pablo and Gil-Castiñeira, Felipe and González-Castaño, Francisco Javier},
  journal={IEEE Open Journal of the Communications Society},
  title={Intelligent Handover Solutions for Heterogeneous B5G Cellular Networks: Proposals and Full-Stack Evaluation},
  year={2026},
  volume={7},
  pages={1--19},
  doi={10.1109/OJCOMS.2025.3649168}
}
