# Near-Miss Prediction Algorithms: Technical Explanation

This document details the three distinct prediction algorithms implemented in the simulator, explaining their logic, mathematical basis, and academic context.

## 1. Baseline Algorithm (Distance-Based)
**File**: `Code/Simulator/Algorithm/baseline_predictor.py`

### Concept
The Baseline algorithm represents the simplest possible approach to risk detection. It ignores motion capability, velocity, and trajectory, relying solely on **Euclidean distance**.

### Implementation Logic
For every object in the frame, the algorithm calculates the distance to the Ego vehicle:
$$ d = \sqrt{(x_{obj} - x_{ego})^2 + (y_{obj} - y_{ego})^2} $$

#### Logic Flow
```text
  [Start: Object Data]
           |
           v
  < Distance < 8.0m? >
    /            \
 [Yes]           [No]
   |               |
   v               v
[Result:        [Result:
 NEAR-MISS]      SAFE]
```

- **Trigger Condition**: If $d < 8.0$ meters, a `NEAR_MISS` is flagged.
- **Conflict Type**: Does not classify conflict types (always `NONE`).
- **Confidence**: Fixed at 0.0 (or 1.0 if triggered, but lacks probabilistic nuance).

### Academic Context
In literature, this serves as a "Naive" or "Proximity-Only" baseline. It is useful for benchmarking to demonstrate that advanced methods (SSM, Learning-based) add value beyond simple proximity sensors. It suffers from high False Positive Rates (FPR) because it flags safe objects like parked cars or vehicles in adjacent lanes that are close but effectively separated.

---

## 2. Rule-Based SSM Algorithm (Deterministic)
**File**: `Code/Simulator/Algorithm/near_miss_predictor.py`

### Concept
This is the standard industry approach for ADAS (Advanced Driver Assistance Systems). It uses **Surrogate Safety Measures (SSM)** derived from physics to assess risk deterministically.

### Key Metrics Implemented
The `SSMCalculator` computes:
1.  **TTC (Time-to-Collision)**:
    $$ TTC = \frac{x_{rel}}{v_{rel}} $$
    *Trigger*: $TTC < 1.5s$ (Critical), $< 2.5s$ (Warning).

2.  **DRAC (Deceleration Rate to Avoid Collision)**:
    $$ DRAC = \frac{v_{rel}^2}{2(x_{rel} - D_{safe})} $$
    *Trigger*: $DRAC > 3.0 m/s^2$ (implies hard braking required).

3.  **MDR (Modified Deceleration Rate)**: Updates DRAC to account for the object's acceleration.

### Conflict Classification logic (`detect_conflict_type`)
The algorithm uses spatial zones and velocity vectors to classify situations into 5 types:
1.  **Rear-End**: Object ahead ($x>0$), same lane ($|y|<1.75m$), moving slower ($v_x < -1.0$).
2.  **Lane-Change**: Object in adjacent lane with lateral velocity ($v_y$) towards Ego, combined with slower longitudinal speed.
3.  **Cutoff**: Aggressive lane change ($v_y$ high, $x$ range close) cutting across Ego's path.
4.  **Broadside**: Object crossing perpendicularly ($|v_y| > 2.0, |v_x| < 5.0$).
5.  **Right-of-Way**: Trajectory intersection prediction where both vehicles arrive at the same point simultaneously.

#### Logic Flow
```text
  [Start: Object State]
           |
   +-------+-------+
   |               |
   v               v
[Calculate SSMs] [Check Conflict Type]
(TTC, DRAC, MDR)  (Rear-End, Cutoff..)
   |               |
   v               |
< Is Critical? >   |
(TTC < 1.5s)       |
   |   \           |
 [No]  [Yes]-----> | -> [NEAR-MISS DETECTED]
   |               |
   v               |
[Count Warnings]   |
   |               |
   v               |
< Criteria >= 2? > |
   |     \         |
 [No]    [Yes]---> | -> [NEAR-MISS DETECTED]
   |               |
   v               |
< Criteria >= 1    |
      AND          |
 Conflict != NONE?>|
   |      \        |
 [No]     [Yes]--> | -> [NEAR-MISS DETECTED]
   |
   v
[Result: SAFE]
```

### Decision Logic
A Near-Miss is flagged if:
- (TTC < Threshold) **OR**
- (DRAC > Threshold) **OR**
- (Risk Level $\ge$ 2 and Conflict Type is identified).

#### Decision Logic Table

This table represents the exact `if-else` flow used in the code to classify a Near-Miss.

| Rule Case | 1. Inherent Risk | 2. Critical Criteria Count* | 3. Conflict Type Detected? | **Result** | Reasoning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `NEAR_MISS` / `COLLISION` | *Ignored* | *Ignored* | **NEAR-MISS** | **Primary Check:** If SSM calculator already flagged high risk, accept it immediately. |
| **2** | `SAFE` / `WARNING` | **$\ge$ 2** | *Ignored* | **NEAR-MISS** | **Multi-Factor Risk:** Two or more safety metrics (e.g., TTC + DRAC) are critical. |
| **3** | `SAFE` / `WARNING` | **1** | **YES** | **NEAR-MISS** | **Context-Aware Risk:** A single metric is critical (e.g., Low TTC) AND a valid conflict pattern (like "Cutoff") confirms intent. |
| **4** | `SAFE` / `WARNING` | 1 | NO | **SAFE** | **Noise Filtering:** Single metric spike without recognized conflict pattern is treated as noise. |
| **5** | `SAFE` / `WARNING` | 0 | *Ignored* | **SAFE** | **No Risk:** No critical thresholds breached. |

*\*Critical Criteria Count is the sum of: (TTC < 1.5s), (DRAC > 3.0), (MDR < Threshold).*

#### Conflict Types Table

| Conflict | Condition (If / Else Logic) |
| :--- | :--- |
| **Rear-End** | IF `ahead` AND `same_lane` AND `vx < -1.0` (Object Slower) |
| **Lane-Change** | IF `adjacent_lane` AND `moving_towards_ego` AND `vx < -2.0` |
| **Cutoff** | IF `ahead` AND (`adjacent` OR `close_lateral`) AND `moving_to_center` (High $v_y$) AND `dx < 20` |
| **Broadside** | IF `|vy| > 2.0` AND `|vx| < 5.0` AND `-10 < dx < 30` |
| **Right-of-Way** | IF `converging_paths` AND `predicted_intersection` closer than `object_length` |
| **NONE** | ELSE return `NONE` |

---

## 3. Stochastic Monte Carlo Algorithm (Probabilistic)
**File**: `Code/Simulator/Algorithm/stochastic_predictor.py`

### Concept
The Stochastic approach acknowledges that sensor data (object position/velocity) is noisy. Instead of trusting a single measurement (which might spike the DRAC calculation erratically), it treats the object's state as a probability distribution.

### Implementation Logic
The algorithm employs a **Monte Carlo Simulation** with $N=30$ particles per object.

1.  **State Perturbation**:
    For each sample $i \in [1..N]$, it generates a perturbed state:
    $$ x_i = x_{obs} + \mathcal{N}(0, \sigma_{pos}) $$
    $$ v_i = v_{obs} + \mathcal{N}(0, \sigma_{vel}) $$
    *Where $\sigma_{pos}=0.5m$, $\sigma_{vel}=1.0m/s$.*

2.  **Ensemble Prediction**:
    It runs the SSM Calculator (TTC, DRAC) on *all 30 samples*.

#### Logic Flow
```text
      [Start: Object State]
               |
               v
     +--> [Loop N=30 Samples] ----+
     |         |                  |
     ^         v                  |
     |   [Perturb State]          |
     | (Add Gaussian Noise)       |
     |         |                  |
     |         v                  |
     |   [Calculate SSMs]         |
     |     (TTC, DRAC)            |
     |         |                  |
     |         v                  |
     |   < Is Unsafe? >           |
     |     /        \             |
     |   [Yes]      [No]          |
     |     |          |           |
     |     v          |           |
     | [Count Unsafe] |           |
     |     |          |           |
     +-----+----------+           |
                                  |
               +------------------+
               |
               v
      [Calculate PoNM]
      (Unsafe Count / N)
               |
               v
       < PoNM > 0.4? >
         /        \
      [Yes]       [No]
        |           |
        v           v
    [Result:     [Result:
   NEAR-MISS]     SAFE]
```

3.  **Probability of Near-Miss (PoNM)**:
    The confidence is calculated as the fraction of samples that violate safety thresholds:
    $$ PoNM = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}(Risk(sample_i) > Threshold) $$

### Decision Logic
- **Trigger**: If $PoNM > 0.4$ (40% of simulated futures are unsafe), a Near-Miss is flagged.
- **Confidence Score**: The $PoNM$ value itself describes the confidence (0.0 to 1.0).

### Advantages
- **Robustness**: Reduces false alarms caused by single-frame sensor noise.
- **Explainability**: Provides a probability score (e.g., "70% chance of collision") rather than a binary Yes/No.
- **Academic Context**: This resembles **Probabilistic Collision Risk Assessment (PCRA)** methods used in autonomous robot navigation, where uncertainty is explicitly modeled rather than ignored.

---

## Comparative Summary

| Feature | Baseline | Rule-Based SSM | Stochastic (Monte Carlo) |
| :--- | :--- | :--- | :--- |
| **Input** | Distance only | Pos, Vel, Acc | Pos distribution, Vel distribution |
| **Physics** | None | Kinematic Equations | Probabilistic Kinematics |
| **Output** | Binary | Binary + Risk Levels | Probability ($0..1$) |
| **Compute** | Very Low | Low | Medium ($30\times$ overhead) |
| **Best For** | Sanity Checks | Standard ADAS | Noisy Sensor Data / Edge Cases |
