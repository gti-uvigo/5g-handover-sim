# Scenario & Waypoints File Format

---

## Scenario Definition File (`sc.txt`)

The scenario file defines the simulation geometry: the bounding area of the deployment, the available frequency bands, and the placement and RF characteristics of each gNodeB.

**Default location:** `handover-simulator/scenario/sc.txt`  
**CLI flag:** `--sc <path>`

### Syntax rules

- Lines starting with `#` are **comments** and are ignored.
- Lines starting with `!` define the **scenario dimensions**.
- Lines starting with `*` define a **frequency band**.
- All other non-empty, non-comment lines define a **gNodeB**.

---

### Section 1 – Scenario dimensions

```
! MinX MaxX MinY MaxY
```

| Field | Description |
|-------|-------------|
| `MinX` | Minimum X coordinate of the simulation area (meters) |
| `MaxX` | Maximum X coordinate of the simulation area (meters) |
| `MinY` | Minimum Y coordinate of the simulation area (meters) |
| `MaxY` | Maximum Y coordinate of the simulation area (meters) |

**Example:**
```
!-400 400 -200 200
```
Defines a 800 m × 400 m rectangular area centred at the origin.

---

### Section 2 – Frequency bands

```
* Band_ID Central_Frequency_Hz User_Bandwidth_Hz GNB_Bandwidth_Hz
```

| Field | Description |
|-------|-------------|
| `Band_ID` | Integer identifier referenced by gNodeBs |
| `Central_Frequency_Hz` | Carrier centre frequency in Hz (e.g., `3.5e9` for 3.5 GHz) |
| `User_Bandwidth_Hz` | Per-user allocated bandwidth in Hz |
| `GNB_Bandwidth_Hz` | Total gNB channel bandwidth in Hz |

**Frequency ranges:**

| Range | Type |
|-------|------|
| 410 MHz – 7.125 GHz | FR1 (sub-6 GHz) |
| 24.25 GHz – 52.6 GHz | FR2 (mmWave) |

**Example:**
```
*0 3.5e9 20e6 400e6    # Band 0: 3.5 GHz FR1, 20 MHz user BW, 400 MHz total BW
*1 28e9 100e6 400e6    # Band 1: 28 GHz FR2, 100 MHz user BW, 400 MHz total BW
```

---

### Section 3 – gNodeBs

```
GNB_ID Position_X Position_Y Position_Z Band_ID Transmission_Power_dBm gNB_Type
```

| Field | Description |
|-------|-------------|
| `GNB_ID` | Zero-based integer identifier |
| `Position_X` | X coordinate in meters |
| `Position_Y` | Y coordinate in meters |
| `Position_Z` | Height in meters |
| `Band_ID` | References a band defined in Section 2 |
| `Transmission_Power_dBm` | Antenna TX power in dBm |
| `gNB_Type` | `I` = isotropic (omnidirectional), `H` = hexagonal trisector |

**Example:**
```
# Micro gNBs on Band 1 (mmWave, low TX power, isotropic)
0 -200.0 50.0 3.0 1 23.0 I
1 -200.0 -50.0 3.0 1 23.0 I
2  0.0   50.0  3.0 1 23.0 I
3  0.0  -50.0  3.0 1 23.0 I
4  200.0 50.0  3.0 1 23.0 I
5  200.0 -50.0 3.0 1 23.0 I

# Macro gNBs on Band 0 (sub-6 GHz, high TX power, hexagonal)
6  0.0  150.0 20.0 0 53.0 H
7  0.0 -150.0 20.0 0 53.0 H
```

### Complete example file

```
# Scenario definition file

# Scenario dimensions
# MinX MaxX MinY MaxY
!-400 400 -200 200

# Bands data
# * Band_ID Central_Frequency_Hz User_Bandwidth_Hz GNB_Bandwidth_Hz
*0 3.5e9 20e6 400e6
*1 28e9 100e6 400e6

# Micro gNBs — Band 1 (28 GHz mmWave)
# GNB_ID  X      Y      Z   Band  Power  Type
0 -200.0  50.0  3.0  1  23.0  I
1 -200.0 -50.0  3.0  1  23.0  I
2    0.0  50.0  3.0  1  23.0  I
3    0.0 -50.0  3.0  1  23.0  I
4  200.0  50.0  3.0  1  23.0  I
5  200.0 -50.0  3.0  1  23.0  I

# Macro gNBs — Band 0 (3.5 GHz FR1)
6    0.0  150.0 20.0  0  53.0  H
7    0.0 -150.0 20.0  0  53.0  H
```

---

## Waypoints File (`wp.txt`)

The waypoints file defines the UE mobility model: named locations in the simulation area, valid spawn points, legal paths between waypoints, and the UE speed range.

**Default location:** `handover-simulator/waypoints/wp.txt`  
**CLI flag:** `--wp <path>` (optional)

### Sections

---

#### `WAYPOINTS`

Named positions in the simulation area.

```
WAYPOINTS
WP_ID  X  Y  Z
```

| Field | Description |
|-------|-------------|
| `WP_ID` | Integer identifier for this waypoint |
| `X`, `Y`, `Z` | Coordinates in meters |

**Example:**
```
WAYPOINTS
0 -200  200 1.5
1 -200    0 1.5
2 -200 -200 1.5
3    0    0 1.5
4  200    0 1.5
5  200  200 1.5
6  200 -200 1.5
```

---

#### `SPAWN_POINTS`

Which waypoints can be used as initial positions for UEs.

```
SPAWN_POINTS
WP_ID
WP_ID
...
```

**Example:**
```
SPAWN_POINTS
0
2
5
6
```

---

#### `LEGAL_PATHS`

Defines which paths between waypoints are valid, and the intermediate waypoints to follow.

```
LEGAL_PATHS
# to from  n_intermediate  wp1  wp2 ...
```

| Field | Description |
|-------|-------------|
| `to` | Destination waypoint ID |
| `from` | Origin waypoint ID |
| `n_intermediate` | Number of intermediate waypoints |
| `wp1 wp2 ...` | Ordered list of intermediate waypoint IDs |

**Example:**
```
LEGAL_PATHS
# to  from  n   intermediates
0  2   1    2
0  5   1    3 4 5
0  6   1    3 4 6
2  0   1    0
2  5   1    3 4 5
2  6   1    3 4 6
5  0   4    3 1 0
5  2   4    3 1 2
5  6   4    6
6  0   4    3 1 0
6  2   4    3 1 2
6  5   4    5
```

---

#### `SPEED_INTERVAL`

Range for the randomised UE speed (m/s).

```
SPEED_INTERVAL
min_speed  max_speed
```

**Example:**
```
SPEED_INTERVAL
1 2
```

UEs will be assigned a speed uniformly sampled from [1, 2] m/s (overridden by `--speed` if supplied via CLI).

---

### Complete example file

```
WAYPOINTS
0 -200  200 1.5
1 -200    0 1.5
2 -200 -200 1.5
3    0    0 1.5
4  200    0 1.5
5  200  200 1.5
6  200 -200 1.5

SPAWN_POINTS
0
2
5
6

LEGAL_PATHS
# to from intermediates
0  2  1  2
0  5  1  3 4 5
0  6  1  3 4 6
2  0  1  0
2  5  1  3 4 5
2  6  1  3 4 6
5  0  4  3 1 0
5  2  4  3 1 2
5  6  4  6
6  0  4  3 1 0
6  2  4  3 1 2
6  5  4  5

SPEED_INTERVAL
1 2
```
