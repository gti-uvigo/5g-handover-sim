# Configuration Reference

`main.py` accepts configuration through **command-line arguments** or a **YAML file** (via `--config`). When both are supplied, the YAML file values take precedence.

---

## Running with default settings

```bash
cd handover-simulator/src
python3 main.py
```

---

## Using a YAML configuration file

```bash
python3 main.py --config my_experiment.yaml
```

Example `my_experiment.yaml`:

```yaml
simTime: 20
nUEs: 10
seed: 42
speed: 15.0
alpha: 8000.0
beta: 2000.0
Hys: 3.0
A3Offset: 2.0
ttt: 0.08
HOInterval: 0.1
sc: ../../handover-simulator/scenario/sc.txt
wp: ../../handover-simulator/waypoints/wp.txt
```

---

## Full Parameter Reference

### General simulation

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--simTime` | float | `10.0` | Total simulation time in seconds. Set to `0` to derive the duration from the waypoints file. |
| `--nUEs` | int | `5` | Number of User Equipment nodes simulated. |
| `--seed` | int | `1234` | Base RNG seed. Each UE gets `seed + ue_index` to ensure independent trajectories. |
| `--logging` | int | `0` | Set to `1` to enable verbose ns-3 component logging. |
| `--config` | str | *(none)* | Path to a YAML configuration file. |
| `--trace` | str | *(none)* | Path to an existing trace folder. When set, ns-3 simulations are skipped and the Python algorithms run directly on the stored traces. |

### Mobility

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--speed` | float | `10.0` | UE speed in m/s. |
| `--trayectoryTime` | float | `5.0` | Duration of each trajectory segment in seconds. |
| `--tolerance` | float | `1.0` | Position matching tolerance in meters for the mobility model. |
| `--wp` | str | `../../handover-simulator/waypoints/wp.txt` | Path to the waypoints file that defines UE movement. |

### Network scenario

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--sc` | str | `../../handover-simulator/scenario/sc.txt` | Path to the scenario definition file. |

### Traffic model

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--packetSize` | int | `1000` | UDP packet size in bytes. |
| `--bitRate` | int | `380000000` | Offered UDP load in bits/s (≈380 Mbps). |
| `--MaxPackets` | int | `0` | Maximum number of packets per flow. `0` = unlimited. |
| `--int` | float | `0.1` | Trace sampling interval in seconds. |

### PHY / error model

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--errorModel` | str | `ns3::NrEesmCcT1` | ns-3 PHY error model. Available options: `ns3::NrEesmCcT1`, `ns3::NrEesmCcT2`, `ns3::NrEesmIrT1`, `ns3::NrEesmIrT2`, `ns3::NrLteMiErrorModel`. |

### 3GPP handover parameters (A3 / CHO)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--Hys` | float | `5.0` | A3 event hysteresis in dBm. Higher values reduce ping-pong handovers. |
| `--A3Offset` | float | `3.0` | A3 offset in dBm added to the serving cell RSRP in the event condition. |
| `--ttt` | float | `0.1` | Time-To-Trigger in seconds. The A3 condition must hold for this duration before a HO is executed. |
| `--NrMeasureInt` | float | `0.1` | NR measurement reporting interval in seconds. |
| `--HOInterval` | float | `0.1` | Minimum interval between consecutive handovers (seconds). |

### SBGH parameters

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--alpha` | float | `5000.0` | Primary scoring weight. Scales the bandwidth-and-RSRP component of the SBGH score. |
| `--beta` | float | `1000.0` | Secondary scoring parameter (reserved for future score components). |

---

## Error Model Options

| Value | Description |
|-------|-------------|
| `ns3::NrEesmCcT1` | Chase Combining, MCS Table 1 (default) |
| `ns3::NrEesmCcT2` | Chase Combining, MCS Table 2 |
| `ns3::NrEesmIrT1` | Incremental Redundancy, MCS Table 1 |
| `ns3::NrEesmIrT2` | Incremental Redundancy, MCS Table 2 |
| `ns3::NrLteMiErrorModel` | LTE Mutual Information error model |

---

## Handover Penalty

The handover penalty is hard-coded in `main.py`:

```python
penalty_dict["Latency"] = 0.020  # 20 ms latency penalty after each handover
```

This penalty is applied to the `Latency` metric of the new serving cell for one `HOInterval` after each handover event, modelling the interruption time during the random access procedure.

---

## Output

When the simulator finishes, a `parameters.json` snapshot is written inside the trace folder:

```json
{
    "debug": 0,
    "simTime": 10.0,
    "max_packets": 0,
    "seed": 1234,
    "nUEs": 5,
    "interval": 0.1,
    "errorModel": "ns3::NrEesmCcT1",
    "tolerance": 1.0,
    "Hys": 5.0,
    "NrMeasureInt": 0.1,
    "A3Offset": 3.0,
    "packetSize": 1000,
    "bitRate": 380000000.0,
    "timeToTrigger": 0.1,
    "speed": 10.0,
    "trayectoryTime": 5.0
}
```

This file is read back when `--trace` is used, ensuring exact reproducibility of the high-level simulation.
