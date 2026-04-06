# Project Knowledge Summary
**Simulator: Deterministic Near-Miss Prediction**
*Written: February 22, 2026*

---

## 1. Project Purpose

This is a **Bird's Eye View (BEV) traffic simulator** built as a thesis research project. Its primary goal is to **predict near-miss events** between an ego vehicle and surrounding traffic objects using physics-based Surrogate Safety Measures (SSMs). The project also investigates a novel probabilistic extension to compare against the deterministic approach, contributing to the academic literature on ADAS (Advanced Driver Assistance Systems) and traffic safety.

---

## 2. High-Level Architecture

```
Simulator/
├── main.py               ← CLI entry point
├── gui_app.py            ← Full Tkinter GUI application
├── demo.py               ← Standalone demo script
│
├── Algorithm/            ← All prediction logic
│   ├── base_algorithm.py       – Abstract interface (NearMissAlgorithm)
│   ├── registry.py             – Plugin registry (AlgorithmRegistry)
│   ├── ssm_calculator.py       – SSM math engine
│   ├── trajectory_model.py     – Trajectory prediction models
│   ├── near_miss_predictor.py  – Main deterministic algorithm (Rule-Based SSM)
│   ├── baseline_predictor.py   – Naive distance-only baseline
│   └── stochastic_predictor.py – Novel Monte Carlo algorithm
│
├── Sources/              ← Data layer
│   ├── scenario_types.py       – Core data structures (dataclasses & enums)
│   ├── data_generator.py       – Synthetic scenario generator
│   └── data_loader.py          – CSV import/export
│
├── Utils/                ← Infrastructure
│   ├── config.py               – All configuration dataclasses & enums
│   ├── visualization.py        – BEV canvas (Tkinter)
│   └── evaluation.py           – Evaluation metrics engine
│
├── Dataset/              ← Generated CSV files + metadata JSON
├── Results/              ← Evaluation output (JSON + TXT reports)
└── docs/ & Documentations/ ← Academic/design documentation
```

---

## 3. Core Data Model (`Sources/scenario_types.py`)

All data flows through these dataclasses:

| Class | Role | Key Fields |
|---|---|---|
| `TrackedObject` | One traffic participant in BEV frame | `object_id`, `x`, `y`, `vx`, `vy`, `length`, `width`, `object_class`, `heading`, `role`, `is_risk_object` |
| `EgoVehicle` | The observing vehicle, always at origin (0,0) | `vx`, `vy`, `length=4.5m`, `width=1.8m` |
| `FrameData` | A single time-step snapshot | `frame_id`, `timestamp`, `ego`, `objects[]`, `ground_truth_events[]` |
| `ScenarioConfig` | Parameters for generating a scenario | `scenario_type`, `duration`, `near_miss_event`, `event_time`, etc. |

### Scenario Types (`ScenarioType` enum)
There are three categories:
- **Near-Miss variants**: `NEAR_MISS_REAR_END`, `NEAR_MISS_LANE_CHANGE`, `NEAR_MISS_CUTOFF`, `NEAR_MISS_BROADSIDE`, `NEAR_MISS_RIGHT_OF_WAY`
- **Safe variants**: `SAFE_REAR_END`, `SAFE_LANE_CHANGE`, `SAFE_CUTOFF`, `SAFE_BROADSIDE`, `SAFE_RIGHT_OF_WAY`
- **Mixed**: `MIXED_NEAR_MISS` — the **only type currently generated** (all 5 near-miss types + safe examples in one scenario, as per research requirement)

---

## 4. Synthetic Data Generator (`Sources/data_generator.py`)

- Class: `SyntheticDataGenerator`
- Sole scenario type generated: `MIXED_NEAR_MISS` (hard-coded by design)
- **Object roles**: `lead`, `adjacent`, `crossing`, `pedestrian`, `background` — role determines initial position and velocity range
- **Stochasticity**: Every frame update applies Gaussian noise to position and velocity with `aggression_factor=3.0`, plus a 10% chance per frame of a sudden "jerk" (velocity impulse)
- **Export**: `DataLoader.export_to_csv()` writes rows with columns: `scenario_id`, `frame_id`, `timestamp`, `object_id`, `object_class`, `x`, `y`, `vx`, `vy`, `length`, `width`, `heading`, `ego_vx`, `ego_vy`, `ground_truth_label`, `conflict_type`, `ttc`
- A companion `_metadata.json` is also written alongside each CSV

---

## 5. Configuration (`Utils/config.py`)

Key configuration dataclasses:

### `SSMThresholds`
| SSM | Safe | Warning | Near-Miss | Collision |
|---|---|---|---|---|
| TTC (s) | > 4.0 | < 4.0 | < 1.0 | 0.0 |
| DRAC (m/s²) | < 2.0 | > 2.0 | > 6.0 | > 8.0 |
| PET (s) | > 2.0 | < 2.0 | < 0.5 | 0.0 |
| MDR | > 1.5 | < 1.5 | < 0.5 | 0.0 |

### `SimulationConfig`
- `dt = 0.1s`, `duration = 10.0s`, `prediction_horizon = 3.0s`
- `ego_velocity = 15.0 m/s` (~54 km/h)
- `lane_width = 3.5m`, `num_lanes = 3`

### `RiskLevel` enum
`SAFE(0)` → `WARNING(1)` → `NEAR_MISS(2)` → `COLLISION(3)`

### `ObjectDimensions`
| Class | Length (m) | Width (m) |
|---|---|---|
| Car | 4.5 | 1.8 |
| Truck | 12.0 | 2.5 |
| Motorcycle | 2.2 | 0.8 |
| Bicycle | 1.8 | 0.6 |
| Pedestrian | 0.5 | 0.5 |

---

## 6. SSM Calculator (`Algorithm/ssm_calculator.py`)

Class: `SSMCalculator`

All measurements are in the **ego-centric BEV frame**: `x` = longitudinal (forward), `y` = lateral (left positive).

### TTC (Time to Collision)
$$TTC = \frac{x_{rel}}{v_{rel}}$$
- Only computed when object is **ahead** (`x > 0`) and **approaching** (relative velocity > 0)
- A 2D variant (`calculate_ttc_2d`) uses quadratic trajectory intersection for non-longitudinal scenarios

### DRAC (Deceleration Rate to Avoid Collision)
$$DRAC = \frac{v_{rel}^2}{2 \cdot d_{longitudinal}}$$
- Only computed when object is ahead and in lateral overlap range

### PET (Post-Encroachment Time)
$$PET = |t_{ego\_at\_point} - t_{obj\_at\_point}|$$
- Computed from trajectory lists; finds when both vehicles occupy the same spatial location

### MDR (Minimum Distance Ratio)
$$MDR = \frac{d_{actual}}{d_{safe\_minimum}}$$
- Values < 1.0 indicate closer than minimum safe distance

### Output: `SSMResult` dataclass
Fields: `object_id`, `ttc`, `ttc_inverse`, `drac`, `pet`, `mdr`, `distance`, `relative_velocity`, `collision_point`, `risk_level`

---

## 7. Trajectory Models (`Algorithm/trajectory_model.py`)

Three models implemented (base class: `TrajectoryModel`):

| Model | Class | Motion Assumption |
|---|---|---|
| Constant Velocity (CV) | `ConstantVelocityModel` | $x(t) = x_0 + v_x \cdot t$ |
| Constant Acceleration (CA) | `ConstantAccelerationModel` | $x(t) = x_0 + v_x t + \frac{1}{2}a_x t^2$ |
| Constant Turn Rate & Velocity (CTRV) | (in file) | Handles curved motion |

The `TrajectoryPredictor` class wraps the CV model and provides `predict_collision_point()` — projects future positions at each timestep and checks for geometric overlap with the ego bounding box.

Uncertainty grows as: `uncertainty = process_noise_std × √t`

---

## 8. Prediction Algorithms

### 8.1 Algorithm Interface (`Algorithm/base_algorithm.py`)

All algorithms extend `NearMissAlgorithm(ABC)` and must implement:
- `predict_scenario(scenario_id, frames) → ScenarioPrediction`
- `get_name() → str` (class method, used for registry key)

`ScenarioPrediction` output fields: `scenario_id`, `predictions[]`, `near_miss_detected`, `first_detection_time`, `max_risk_level`, `max_confidence`, `summary{}`

### 8.2 Algorithm Registry (`Algorithm/registry.py`)

`AlgorithmRegistry` is a class-level dictionary. Algorithms self-register via the `@AlgorithmRegistry.register` decorator on their class definition. The GUI uses `AlgorithmRegistry.list_algorithms()` to populate the algorithm selector dropdown dynamically.

### 8.3 Rule-Based SSM Predictor — `NearMissPredictor` (`near_miss_predictor.py`)

**Name in registry**: `"Rule-Based SSM"`

**Conflict type detection** (5 types):
| Type | Trigger Condition |
|---|---|
| `REAR_END` | Object ahead, same lane (`\|y\| < lane_width/2`), slower (`vx < -1.0`) |
| `LANE_CHANGE` | Adjacent lane, lateral motion toward ego, much slower (`vx < -2.0`) |
| `CUTOFF` | Ahead, aggressive lateral cut (`vy > 1.0`), close range (`dx < 20m`) |
| `BROADSIDE` | High lateral velocity (`\|vy\| > 2.0`), near intersection (`-10 < dx < 30`) |
| `RIGHT_OF_WAY` | Trajectory intersection predicted where both reach same point simultaneously |

**Near-miss classification rules** (`_classify_near_miss`):
1. Risk level is `NEAR_MISS` or `COLLISION` → True
2. `criteria_met >= 2` (any combination of TTC/DRAC/MDR critical) → True
3. `criteria_met >= 1` AND `conflict_type != NONE` → True

**Confidence score** (`_calculate_confidence`):
- Base: 0.5
- +0.1 if history ≥ 5 frames; +0.1 if history ≥ 15 frames
- +0.2 if 2 SSMs agree on risk; +0.1 if all 3 agree
- +0.1 if a conflict type is identified
- Capped at 1.0

**Object tracking**: Maintains a rolling 30-frame history per `object_id` to support confidence scoring and CA model acceleration estimation.

### 8.4 Baseline Predictor — `DistancePredictor` (`baseline_predictor.py`)

**Name in registry**: `"Baseline (Distance Only)"`

- Single rule: if Euclidean distance < **8.0 meters** → `NEAR_MISS`
- Ignores velocity, heading, and trajectory
- Confidence: 1.0 if triggered, 0.0 otherwise
- Academic purpose: demonstrates the gap between naive proximity detection and SSM-based methods (expected higher FPR due to flagging parked/adjacent lane vehicles)

### 8.5 Stochastic Predictor — `StochasticPredictor` (`stochastic_predictor.py`)

**Name in registry**: `"Stochastic (Monte Carlo)"`

**Novel method** proposed in the thesis gap analysis:

1. For each frame, generate **N=30 particle samples** by adding Gaussian noise to the object's state:
$$P_{sample}^{(i)} \sim \mathcal{N}(P_{observed}, \Sigma_{noise})$$
   - `pos_uncertainty_std = 0.5m`, `vel_uncertainty_std = 1.0 m/s`, `acc_uncertainty_std = 2.0 m/s²`

2. Calculate SSMs for **each sample** against the ego vehicle

3. Derive the **Probability of Near-Miss (PoNM)**:
$$PoNM = \frac{\sum_{i=1}^{N} \mathbb{1}(TTC_i < \tau)}{N}$$

4. Use `PoNM` as the continuous `confidence` score (0.0–1.0), compared against a threshold (0.3) to produce a binary near-miss flag

**Purpose**: Addresses the "binary rigidity" gap of the deterministic approach — a scenario with TTC=1.51s and TTC=1.49s receive very different treatment in the Rule-Based system but nearly identical PoNM scores in the Stochastic system.

---

## 9. Evaluation Framework (`Utils/evaluation.py`)

Class: `Evaluator`

### Standard Classification Metrics (`ConfusionMatrix`)
| Metric | Formula |
|---|---|
| Accuracy | $(TP + TN) / Total$ |
| Precision | $TP / (TP + FP)$ |
| Recall | $TP / (TP + FN)$ |
| F1 Score | $2PR / (P + R)$ |
| FPR | $FP / (FP + TN)$ |
| FNR | $FN / (FN + TP)$ |

### Advanced Metrics (`EvaluationResults`)
| Metric | Description |
|---|---|
| **Brier Score** | $\frac{1}{N}\sum(p_i - o_i)^2$ — MSE for probabilistic forecasts; works for both binary (Deterministic, where p=0 or 1) and continuous (Stochastic) predictions |
| **AUROC** | Area under ROC curve; Deterministic = single point, Stochastic = full curve |
| **Mean Detection Time** | Average time before event when near-miss was first flagged |
| **Temporal IoU (t-IoU)** | $\frac{Duration(GT \cap Pred)}{Duration(GT \cup Pred)}$ — how well the predicted time interval overlaps ground truth |
| **Type Accuracy (Sequence-Level)** | Classification accuracy for conflict types, only counted where t-IoU > 0.5 |
| **Type Confusion Matrix** | Multi-class matrix for the 5 conflict types |
| **SSM Statistics** | Mean/std/min/max of TTC and DRAC values |
| **Risk Distribution** | Count of frames per RiskLevel |
| **Reliability Diagram** | Calibration curve data for PoNM |

### Results Persistence
`Evaluator.save_results(results)` writes:
- `Results/evaluation_YYYYMMDD_HHMMSS.json` — machine-readable
- `Results/evaluation_YYYYMMDD_HHMMSS.txt` — human-readable report

---

## 10. BEV Visualization (`Utils/visualization.py`)

Class: `BEVVisualizer` (Tkinter Canvas)

- **Coordinate system**: BEV x=forward, y=left-positive; mapped to Canvas x=right, y=down
- **View window**: -20m to +80m longitudinal, -15m to +15m lateral
- **Road rendering**: Solid edge lines (white), dashed lane dividers (white), center line (yellow)
- **Object rendering**: Rotated bounding boxes colored by risk level overlay on class base color
- **Risk colors**: SAFE=green, WARNING=yellow, NEAR_MISS=orange, COLLISION=red
- **Class colors**: car=cornflower blue, truck=brown, motorcycle=deep pink, bicycle=spring green, pedestrian=gold
- Velocity vectors drawn as arrows from object centers
- Warning labels displayed above near-miss objects

---

## 11. GUI Application (`gui_app.py`)

Class: `NearMissSimulatorApp` (Tkinter, 1648 lines)

Key panels:
- **Data Generation Panel**: Configure num_scenarios, seed, object counts → calls `SyntheticDataGenerator`
- **Scenario Editor**: Frame-by-frame editor with an `ObjectEditorDialog` popup; allows manually adding/editing `TrackedObject` instances with full field control; physics-based interpolation between keyframes
- **Algorithm Selector**: Dropdown populated from `AlgorithmRegistry.list_algorithms()` — switches between Rule-Based SSM, Baseline, and Stochastic at runtime
- **BEV Canvas**: Live playback of generated/loaded scenarios using `BEVVisualizer`; play/pause/step controls
- **Info Panel**: Right-side panel showing per-object SSM values, risk levels, and warning messages
- **Evaluation Panel**: Runs `Evaluator`, displays confusion matrix, F1, detection times, Brier Score, AUROC

---

## 12. Gap Analysis & Research Novelty

*(From `gap_analysis_and_novelty.md`)*

### Identified Gaps in Current (Deterministic) Approach
1. **Binary rigidity**: Hard threshold creates cliff-edge decisions (TTC=1.51s is "Safe", 1.49s is "Risk")
2. **Ignored uncertainty**: `TrajectoryPredictor` computes uncertainty bounds but `SSMCalculator` uses only the mean position
3. **Missing tail risk**: In stochastic traffic, the mean trajectory may appear safe while a plausible deviation is fatal

### Proposed Novelty: "Stochastic Monte Carlo SSM Fusion"
- Bridges **interpretability of SSMs** (vs. black-box neural nets) with **robustness of probabilistic methods** (vs. rigid rule-based)
- Outputs continuous PoNM rather than binary flag
- Enables new evaluation metrics (Brier Score, AUROC, Risk Uncertainty)
- Potential paper framing: *"Probabilistic Risk Assessment in Stochastic Mixed-Traffic Environments using Ensemble Surrogate Safety Measures"*

### Related Work Context
| Approach | Used In | Limitation This Project Addresses |
|---|---|---|
| Spatiotemporal GNNs | 2022 | Black-box, high inference cost |
| Hybrid CNN + SSM | 2023 | Requires labeled heatmap datasets |
| Probabilistic TTC | 2022 | Sensitive to covariance estimation |
| Potential Fields | 2021 | Difficult manual coefficient tuning |
| Adaptive SSMs | 2024 | Requires unavailable environmental metadata |

---

## 13. Evaluation Theory & Metrics Hierarchy

*(From `docs/evaluation_theory_plan.md` and `comparable_evaluation_metrics.md`)*

### Three Evaluation Levels
| Level | View | Key Metric | What It Catches |
|---|---|---|---|
| Frame-Level | "micro" | Frame-F1, AUC-ROC | Flickering, latency |
| Event-Level | "macro" | Temporal IoU > 0.5 | Duration accuracy |
| Safety-Level | "operational" | Time-to-Accident (TTA) | Warning earliness |

### Evaluating Deterministic vs. Stochastic Fairly
The fundamental challenge: Algorithm A outputs binary (0/1), Algorithm B outputs probability [0,1].

**Solution — Proper Scoring Rules**:
- **Brier Score**: Works for both; deterministic is special case (p=0 or 1)
- **AUROC**: Deterministic = one point on the ROC plot; Stochastic = full curve
- **Robustness Consistency (RC)**: Plot F1 vs. sensor noise level σ; $RC = dM/d\sigma$; Stochastic expected to degrade more gradually

### Known Data Generator Limitations (Noted for Future Work)
1. Standard (non-mixed) scenarios assign roles like `"lead"` without `is_risk_object=True`, breaking frame-level ground truth evaluation
2. Ground truth events use a fixed 0.5s time window around `event_time` rather than physics-derived TTC threshold crossings
3. Correction path: tag risk objects explicitly + derive ground truth from TTC < 1.5s check at each frame

---

## 14. Dataset Format

CSV columns:
```
scenario_id, frame_id, timestamp, object_id, object_class,
x, y, vx, vy, length, width, heading,
ego_vx, ego_vy, ground_truth_label, conflict_type, ttc
```

- `ground_truth_label`: `"near_miss"` or `"None"` (populated from `FrameData.ground_truth_events`)
- `conflict_type`: e.g. `"near_miss_rear_end"` when applicable
- Companion `_metadata.json` stores scenario-level statistics

---

## 15. Dependencies

```
numpy >= 1.21.0      # Numerical computation
pandas >= 1.3.0      # Data handling
matplotlib >= 3.4.0  # Plotting (evaluation charts)
pillow >= 8.0.0      # Image handling
scipy >= 1.7.0       # Optional, advanced features
tkinter              # GUI (Python built-in)
```

---

## 16. Entry Points

| Script | Purpose |
|---|---|
| `python3 main.py` | Launch GUI |
| `python3 main.py --generate --scenarios 50 --output data.csv` | CLI data generation |
| `python3 main.py --input data.csv --evaluate` | CLI prediction + evaluation |
| `python3 demo.py` | Standalone demonstration of the full pipeline |

---

## 17. Key Design Decisions & Patterns

1. **Ego-centric BEV frame**: All object positions are relative to the ego vehicle (ego always at origin). This simplifies SSM calculations and reflects how ADAS sensors work.

2. **Modular algorithm plugin system**: New algorithms only need to subclass `NearMissAlgorithm`, implement `predict_scenario()`, and decorate with `@AlgorithmRegistry.register` — GUI picks them up automatically.

3. **Separation of concerns**: Data layer (`Sources/`) never imports from `Algorithm/`; Algorithm layer never imports from `Utils/visualization`; evaluation imports both but only reads outputs.

4. **Ground truth embedding**: Ground truth events are carried inside `FrameData.ground_truth_events[]` so the evaluation module can compare prediction vs. truth without a separate ground-truth file.

5. **Confidence as PoNM**: The `max_confidence` field in `ScenarioPrediction` serves dual purpose — it captures the probabilistic score from the Stochastic algorithm and a heuristic certainty score from the Deterministic algorithm, enabling unified comparison via Brier Score.
