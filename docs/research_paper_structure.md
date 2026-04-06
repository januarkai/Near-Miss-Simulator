# Research Paper Structure

**Proposed Title:** *Stochastic Ensemble Surrogate Safety Measure Fusion for Robust Near-Miss Prediction in Synthetic Mixed-Traffic Simulation*

**Target Venues (in priority order):**
1. *Analytic Methods in Accident Research* (AMAR) — highest relevance; Paper 1 (Jiao et al. 2024) is direct competitor
2. *Accident Analysis & Prevention* (AAP) — strong fit; Papers 2, 8, 9 published here
3. *IEEE Transactions on Intelligent Transportation Systems* (T-ITS) — broader audience; Papers 4, 8, 11 aligned here

---

## Section 1 — Introduction

### 1.1 Problem Motivation
- Near-miss events are established pre-crash indicators: they occur ~500× more frequently than crashes yet capture the same causal mechanisms (AASHTO, NHTSA).
- Early and accurate near-miss detection enables real-time ADAS intervention and retrospective road safety analysis.
- Traditional traffic safety relies on post-hoc crash records; near-miss studies allow proactive risk quantification without waiting for fatalities.

### 1.2 Limitations of Existing Deterministic SSM Systems
- **Binary rigidity**: A hard TTC threshold (e.g., 1.0 s) makes TTC=1.51 s "Safe" and TTC=1.49 s "Near-Miss" — a cliff-edge decision that does not reflect physical reality.
- **Ignored measurement uncertainty**: Real sensor inputs (radar, LiDAR, camera) carry positional and velocity noise; deterministic SSM systems use the mean observation only, discarding uncertainty structure.
- **Missed tail risk**: In stochastic traffic, the mean trajectory may appear safe while a low-probability deviation is catastrophic.
- **Single-metric brittleness**: TTC alone fails for lateral conflicts (lane-change, broadside); DRAC alone is undefined at zero relative velocity. No single SSM universally covers all 5 conflict types.

Key citations: Jiao et al. (2024), de Gelder et al. (PRISMA, 2023), Paper 3 (Li et al. 2D-TTC accuracy study).

### 1.3 Research Gap Statement
> *No prior work provides a simulation-based, interpretable, training-data-free probabilistic SSM framework that (1) covers all five mixed-traffic conflict types (rear-end, lane-change, cut-off, broadside, right-of-way), (2) outputs a continuous Probability of Near-Miss (PoNM) score, and (3) evaluates robustness under controlled noise levels using proper scoring rules (Brier Score, AUROC, Temporal IoU).*

Gap breakdown:
| Gap | Evidence |
|---|---|
| Probabilistic SSMs require learning-based components | Papers 1, 2, 3, 8 |
| Multi-type coverage in one framework is absent | Papers 3, 9 (single-scenario studies) |
| Noise robustness not systematically evaluated | Papers 1, 2, 10 (no σ-sweep experiments) |
| Interpretability lost in deep-learning extensions | Papers 4, 5 (LSTM/GPR black-boxes) |

### 1.4 Contribution Claims
1. **Synthetic BEV simulation framework**: A Python-based ego-centric Bird's Eye View simulator generating `MIXED_NEAR_MISS` scenarios with five conflict types embedded in stochastic traffic noise.
2. **Rule-Based SSM baseline**: A deterministic multi-SSM predictor (TTC, DRAC, MDR) covering all five conflict types as a reproducible benchmark.
3. **Stochastic Monte Carlo SSM Fusion (novel)**: N=30 Gaussian-perturbed particle samples evaluated through the SSM pipeline; ensemble fraction yields a continuous PoNM score without any trained model.
4. **Unified evaluation framework**: Brier Score, AUROC, Temporal IoU (t-IoU), and Time-to-Accident (TTA) applied comparably to both deterministic (binary) and probabilistic (continuous) algorithms.
5. **Robustness characterisation**: Controlled noise-level experiments ($\sigma \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$) quantify graceful degradation of the Stochastic method vs. cliff-edge collapse of the Rule-Based method.

### 1.5 Paper Organisation
Brief paragraph mapping each section to a contribution.

---

## Section 2 — Related Works

### 2.1 Surrogate Safety Measures: Foundations
- **TTC** (Hayward, 1972): longitudinal time to collision assuming constant velocity; most widely used SSM; 1D formulation biases results for lateral scenarios by up to 300% (Paper 3, Li et al.).
- **DRAC** (Cooper & Ferguson, 1976): deceleration required to avoid collision; complements TTC for rear-end rear-approach.
- **PET** (Allen et al., 1978): Post-Encroachment Time; gold standard for crossing/broadside conflicts (Paper 12, Anowar et al.).
- **MDR** (Minimum Distance Ratio): spatial conflict measure; adds geometric proximity dimension.

Key insight: No single SSM is universally valid; conflict-type-aware SSM routing is required (motivates our multi-SSM architecture).

### 2.2 Probabilistic and Uncertainty-Aware SSM Extensions
- **PRISMA** (de Gelder et al., 2023, AAP): defines conflict probability via extreme value theory on naturalistic data; requires field data collection; longitudinal conflicts only.
- **Jiao et al.** (2024, AMAR): unified probabilistic framework $P(\text{conflict}) = P(\text{proximity} < \tau_{\text{context}})$; context-adaptive thresholds; relies on environmental metadata not always available.
- **Probabilistic TTC frameworks** (Papers 2, 3): Gaussian TTC distributions; sensitive to covariance tuning; no multi-type coverage.

Key insight: These methods improve calibration but require real-world data, regression models, or environmental metadata. Our Monte Carlo approach produces probabilistic output with zero training data.

### 2.3 Trajectory Prediction for Conflict Detection
- **Seq2Seq LSTM** (Paper 4, 2022): predicts future trajectories at intersections; achieves state-of-art recall but requires large labeled datasets and loses interpretability.
- **Gaussian Process Regression** (Paper 5, 2022): uncertainty-aware trajectory forecasting; high computational cost at inference.
- **2D-TTC conflict detection** (Paper 9): lateral trajectory intersection for lane-change scenarios; shows 2D formulation reduces false negatives by 38% vs. 1D TTC.

Key insight: Deep-learning trajectory predictors achieve high accuracy but at the cost of interpretability and training data. Our method bypasses trajectory prediction in favour of SSM-on-particles evaluation.

### 2.4 Multi-Vehicle and Contextual Conflict Analysis
- **Del Re et al.** (Paper 7): 3-vehicle interaction chains create secondary conflicts invisible to pairwise pairwise SSM analysis; propagation modelling is open problem.
- **Al-Haideri** (Paper 10): driver behaviour classification (defensive/aggressive) provides critical context for interpreting SSM values; shows threshold sensitivity is behaviour-dependent.
- **Abdel-Aty et al.** (Paper 6, 2023): comprehensive survey of CV-based safety analysis — confirms BEV representation is the emerging standard for multi-class traffic safety studies.

### 2.5 Evaluation Methodologies
- Most prior work uses scenario-level Precision/Recall only; event-level or temporal metrics are rare.
- **Brier Score** as a proper scoring rule for probabilistic safety predictions: Jiao et al. (2024) use it; standard in meteorological forecasting.
- **AUROC** for comparing deterministic vs. probabilistic systems on equal footing: requires thresholding deterministic outputs to a single ROC point.
- **Temporal IoU** for measuring event duration accuracy (rarely used in traffic safety — gap this paper addresses).

### 2.6 Positioning Table
| Method | Interpretable | No Training Data | Multi-Type | Probabilistic | Noise Robustness Studied |
|---|---|---|---|---|---|
| **Stochastic MC-SSM (ours)** | ✓ | ✓ | ✓ | ✓ | ✓ |
| Rule-Based SSM (ours, baseline) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Jiao et al. 2024 | ✗ (learning) | ✗ | ✓ | ✓ | ✗ |
| PRISMA 2023 | ✗ (regression) | ✗ | ✗ | ✓ | ✗ |
| Seq2Seq LSTM 2022 | ✗ | ✗ | ✗ | ✗ | ✗ |
| 2D-TTC 2023 | ✓ | ✓ | ✗ (lateral only) | ✗ | ✗ |

---

## Section 3 — Methodology

### 3.1 System Architecture Overview
- Ego-centric Bird's Eye View (BEV) coordinate frame: ego vehicle always at origin (0, 0); positive x = forward, positive y = left.
- Four-layer pipeline: **Data Generation → Algorithm Prediction → Ground Truth Labelling → Evaluation**.
- Plugin-based algorithm registry: new algorithms self-register via `@AlgorithmRegistry.register`; GUI and CLI pick them up automatically.

### 3.2 Synthetic Data Generation
- **Scenario type**: `MIXED_NEAR_MISS` — ego embedded in 3–7 surrounding vehicles from five object classes (car, truck, motorcycle, bicycle, pedestrian) with roles (lead, adjacent, crossing, pedestrian, background).
- **Stochastic dynamics**: position noise `σ_p = 0.3 m`, velocity noise `σ_v = 0.5 m/s`; aggression factor 3.0×; 10% jerk probability per frame; 5% lateral swerve probability.
- **Simulation parameters**: `dt = 0.1 s`, `prediction_horizon = 3.0 s`, `ego_velocity = 15.0 m/s` (~54 km/h), `lane_width = 3.5 m`.
- **Ground truth**: `is_risk_object = True` on primary risk object; event window derived from TTC < 1.5 s check per frame.
- **Conflict embedding**: all five conflict types can co-occur in one scenario; ground truth conflict type recorded in `FrameData.ground_truth_events[]`.

### 3.3 SSM Calculator
Four SSMs computed per object per frame:

| SSM | Formula | Use Case |
|---|---|---|
| TTC (1D) | $TTC = \frac{d_x - L_{obj}/2}{|v_{rel,x}|}$ | Rear-end scenarios |
| TTC (2D) | Quadratic trajectory intersection with bounding box overlap check | Lane-change and cut-off scenarios |
| DRAC | $DRAC = \frac{v_{rel,x}^2}{2 \cdot d_x}$ | Rear-approach deceleration requirement |
| MDR | $MDR = \frac{d_{current}}{d_{initial}}$ | Spatial closure rate |

**SSM thresholds**:
| SSM | Safe | Warning | Near-Miss |
|---|---|---|---|
| TTC | > 4.0 s | < 4.0 s | < 1.0 s |
| DRAC | < 3.0 m/s² | 3–6 m/s² | > 6.0 m/s² |
| MDR | > 0.8 | 0.5–0.8 | < 0.5 |

### 3.4 Conflict Type Classification
Five conflict types with detection logic:

| Type | Detection Condition |
|---|---|
| `REAR_END` | Object ahead, same lane ($\|y\| < w_{lane}/2$), slower ($v_{rel,x} < -1.0$) |
| `LANE_CHANGE` | Adjacent lane, lateral approach toward ego, much slower ($v_{rel,x} < -2.0$) |
| `CUTOFF` | Ahead, aggressive lateral cut ($v_y > 1.0$), close ($d_x < 20$ m) |
| `BROADSIDE` | High lateral velocity ($\|v_y\| > 2.0$), near intersection ($-10 < d_x < 30$) |
| `RIGHT_OF_WAY` | Predicted trajectory intersection at same spatial point simultaneously |

### 3.5 Algorithm Descriptions

#### Algorithm A: Baseline (Distance Only)
- Binary rule: Euclidean distance < 8.0 m → `NEAR_MISS`.
- Ignores velocity, heading, and trajectory; confidence = 1.0 or 0.0.
- Academic purpose: establishes the lower bound; demonstrates the gap between naive proximity and SSM-based reasoning.

#### Algorithm B: Rule-Based SSM (Deterministic)
- Evaluates TTC, DRAC, MDR per object per frame; classifies risk level as `SAFE / WARNING / NEAR_MISS / COLLISION`.
- Near-miss is flagged when: (i) risk level is `NEAR_MISS` or `COLLISION`, OR (ii) ≥2 SSMs indicate critical values, OR (iii) ≥1 SSM critical AND conflict type is identified.
- Confidence score: base 0.5 + history bonus (+0.1/+0.1) + SSM agreement bonus (+0.2/+0.1) + conflict type bonus (+0.1), capped at 1.0.

#### Algorithm C: Stochastic Monte Carlo SSM Fusion (Proposed)
- For each frame, generate N=30 particle samples by perturbing the observed state with Gaussian noise:
$$\mathbf{X}^{(i)}_{\text{sample}} \sim \mathcal{N}\!\left(\mathbf{X}_{\text{obs}},\ \Sigma_{\text{noise}}\right), \quad i = 1,\ldots,N$$
where $\sigma_p = 0.5$ m, $\sigma_v = 1.0$ m/s, $\sigma_a = 2.0$ m/s².
- Evaluate TTC for each particle through the SSM pipeline.
- Derive the **Probability of Near-Miss (PoNM)**:
$$PoNM = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}\!\left(TTC^{(i)} < \tau_{\text{near\_miss}}\right)$$
- PoNM is the continuous `confidence` score; binary flag: `PoNM > 0.3`.
- Rationale: TTC=1.51 s and TTC=1.49 s receive nearly equal PoNM, while the Rule-Based system treats them as "Safe" vs. "Near-Miss" respectively.

### 3.6 Evaluation Framework

#### 3.6.1 Standard Event-Level Metrics
- Confusion matrix at scenario level: TP, TN, FP, FN → Accuracy, Precision, Recall, F1, FPR, FNR.

#### 3.6.2 Probabilistic Quality Metrics
- **Brier Score**: $BS = \frac{1}{N}\sum_{i=1}^{N}(p_i - o_i)^2$ — proper scoring rule valid for both deterministic (p ∈ {0,1}) and probabilistic (p ∈ [0,1]) predictions.
- **AUROC**: Deterministic algorithm = single point on ROC plot; Stochastic algorithm = full ROC curve using PoNM as the ranking score.

#### 3.6.3 Temporal Quality Metrics
- **Temporal IoU (t-IoU)**: $t\text{-}IoU = \frac{|GT \cap Pred|}{|GT \cup Pred|}$ — measures how well the predicted near-miss time interval overlaps the ground truth interval.
- **Time-to-Accident (TTA)** / Mean Detection Time: average lead time before event when near-miss was first flagged; higher is better.
- **Type Confusion Matrix**: conflict type classification accuracy (only counted where t-IoU > 0.5 at event level).

#### 3.6.4 Robustness Study
- Sweep position noise standard deviation $\sigma \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$ m.
- At each noise level, run full evaluation on both algorithms.
- Plot: F1 vs. σ (Rule-Based) vs. Brier Score vs. σ (Stochastic).
- Robustness Consistency (RC): slope of metric degradation curve $dM/d\sigma$; lower magnitude = more robust.

---

## Section 4 — Results

### 4.1 Experimental Setup
- Dataset: N scenarios generated with `SyntheticDataGenerator`, seed fixed for reproducibility.
- Reported datasets: `2026121701_test_dataset.csv` (2026-12-17), `2026021702_test_dataset.csv` (2026-02-17).
- Evaluation run via `Evaluator` class; all results saved to `Results/`.

### 4.2 Overall Performance Comparison
Present a summary table:

| Algorithm | Precision | Recall | F1 | Brier Score ↓ | AUROC ↑ | Mean TTA (s) ↑ |
|---|---|---|---|---|---|---|
| Baseline (Distance) | — | — | — | — | — | — |
| Rule-Based SSM | — | — | — | — | (point) | — |
| Stochastic MC-SSM | — | — | — | — | (curve) | — |

**Expected pattern**: Baseline shows highest FPR (flags parked/adjacent vehicles); Rule-Based shows good F1 at low noise; Stochastic shows lower Brier Score and higher AUROC at all noise levels; Stochastic shows earlier TTA (longer lead time).

### 4.3 Robustness Analysis (Key Result)
- Present Figure: F1 and Brier Score vs. noise level σ for all three algorithms.
- **Key thesis result**: Rule-Based F1 shows cliff-edge collapse above σ ≈ 1.0 m; Stochastic Brier Score degrades linearly/gradually.
- Quantify Robustness Consistency: $RC_{\text{Rule-Based}} \gg RC_{\text{Stochastic}}$ (larger slope magnitude = less robust).

### 4.4 Temporal Quality
- Present histogram or CDFs of t-IoU scores per algorithm.
- Present detection time distribution (time before event of first near-miss flag): Stochastic expected to flag earlier due to PoNM rising gradually vs. Rule-Based step function.
- **Expected finding**: Stochastic mean detection time is T seconds earlier than Rule-Based (advantage for ADAS warning lead time).

### 4.5 Per-Conflict-Type Analysis
- Type confusion matrix heatmap for Rule-Based and Stochastic.
- Identify which conflict types each algorithm struggles with:
  - Rule-Based expected to fail on `LANE_CHANGE` and `CUTOFF` (1D TTC bias for lateral scenarios; see Literature Paper 3).
  - Stochastic expected to have higher recall for `BROADSIDE` and `RIGHT_OF_WAY` (uncertainty sampling covers edge cases).

### 4.6 Calibration Analysis (Stochastic only)
- Reliability diagram: PoNM bins vs. actual near-miss rate.
- A well-calibrated model sits on the diagonal $y = x$.
- Expected finding: Stochastic PoNM is roughly calibrated without any post-processing (unlike learning-based methods requiring temperature scaling).

### 4.7 Qualitative Case Studies
- **Case 1: Marginal rear-end** — TTC = 1.05 s; Rule-Based is "Near-Miss" (correctly); Stochastic PoNM ≈ 0.70 (high, correct). Show BEV frame snapshot.
- **Case 2: False positive by distance baseline** — Object in adjacent lane at 7.5 m; Baseline flags "Near-Miss"; Rule-Based and Stochastic correctly "Safe" (no trajectory overlap).
- **Case 3: Near-threshold uncertainty** — TTC = 1.03 s in mean, but pedestrian uncertainty high; Rule-Based "Near-Miss"; Stochastic PoNM ≈ 0.52 (moderate); this is the key illustration of probabilistic advantage.

---

## Section 5 — Discussion

### 5.1 Interpretation of Key Results
- The PoNM score adds an uncertainty layer to traditional binary SSM outputs — directly addressing the "binary rigidity" gap without requiring any training data.
- Graceful noise degradation is the primary practical advantage: in real-world deployment, sensor noise is unavoidable; an algorithm that degrades linearly rather than catastrophically is safer.
- Stochastic algorithm requires 30× more SSM evaluations per frame — discuss computational cost; remain real-time at typical 10 Hz sensor rates.

### 5.2 Comparison to Prior Work

Because each prior method uses a different dataset and experimental setup, a direct head-to-head numeric comparison is not possible. Instead, the comparison is structured around **which metrics each paper reports** and **whether our method can produce the same metric type** — allowing an apple-to-apple discussion of methodology quality.

| Metric | This Work (Stochastic MC-SSM) | Jiao et al. 2024 (AMAR) | PRISMA / de Gelder 2023 (AAP) | Seq2Seq LSTM 2022 (TITS) | 2D-TTC Study 2023 (AAP) | Al-Haideri 2021 |
|---|---|---|---|---|---|---|
| **Precision** | ✓ (reported) | ✓ | ✓ | ✓ | ✓ | ✗ |
| **Recall** | ✓ (reported) | ✓ | ✓ | ✓ | ✓ | ✗ |
| **F1 Score** | ✓ (reported) | ✓ | ✗ | ✓ | ✓ | ✗ |
| **AUROC** | ✓ full curve | ✓ | ✓ | ✗ | ✗ | ✗ |
| **Brier Score** | ✓ (reported) | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Temporal IoU (t-IoU)** | ✓ (novel in this work) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Time-to-Accident (TTA)** | ✓ (reported) | ✗ | ✗ | ✓ (detection latency) | ✗ | ✗ |
| **False Positive Rate (FPR)** | ✓ (reported) | ✓ | ✓ | ✗ | ✓ | ✗ |
| **Calibration (reliability diagram)** | ✓ (PoNM bins vs. actual rate) | ✓ | ✗ | ✗ | ✗ | ✗ |
| **Robustness vs. noise level (σ-sweep)** | ✓ (novel in this work) | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Per-conflict-type accuracy** | ✓ (type confusion matrix) | ✗ | ✗ | ✓ (intersection subtypes) | ✗ (rear-end only) | ✗ |
| **Probabilistic output (continuous score)** | ✓ PoNM ∈ [0, 1] | ✓ | ✓ | ✗ (binary) | ✗ (binary) | ✗ |
| **No training data required** | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ |

**Discussion notes per comparison**:

- **Vs. Jiao et al. (2024, AMAR)**: Both report Brier Score, AUROC, and precision/recall — the most directly comparable pair. Key differentiator: Jiao et al. train on naturalistic data; this work uses simulation with controlled noise injection. This work additionally reports t-IoU and the σ-robustness curve, which Jiao et al. do not.
- **Vs. PRISMA / de Gelder (2023, AAP)**: PRISMA reports AUROC and FPR well, but does not report Brier Score, t-IoU, or per-type accuracy. PRISMA is longitudinal-only; our framework covers all five conflict types. Comparison is limited to AUROC and FPR values.
- **Vs. Seq2Seq LSTM (2022, TITS)**: Shares F1, recall, and detection latency (TTA proxy); these are directly discussable. LSTM does not produce calibrated probabilities, so Brier Score and AUROC cannot be compared. Key argument: our method matches or approaches recall without training data.
- **Vs. 2D-TTC Study (2023, AAP)**: Shares precision, recall, F1, and FPR; direct numeric discussion is feasible for the lateral conflict types (lane-change, cut-off). This work goes beyond by adding probabilistic scoring on top of the 2D geometry.
- **Vs. Al-Haideri (2021)**: Primarily a behavioural/threshold study — no standard classification metrics reported; comparison is qualitative only (threshold sensitivity discussion in Section 5.3 limitations).

### 5.3 Limitations
- Synthetic data only: ego-centric BEV simulation does not capture all real-world complexities (occlusion, V2X communication failures, multi-sensor fusion noise).
- 1D TTC used for rear-end only: lateral scenarios would benefit from activating `calculate_ttc_2d()` (future work; see Phase 1 research plan).
- PET not yet integrated: `calculate_pet()` is implemented but not used in classification; crossing scenarios are under-served.
- Multi-vehicle chain effects not modelled: pairwise-only analysis misses secondary conflicts documented by Del Re et al. (Paper 7).
- N=30 samples: may under-sample the tail of the distribution for extreme noise conditions.

---

## Section 6 — Conclusion

### 6.1 Summary of Contributions
- Presented a **synthetic BEV near-miss simulation framework** covering five mixed-traffic conflict types and three integrated algorithms.
- Demonstrated that **Rule-Based SSM** provides competitive F1 at low noise but suffers categorical collapse as sensor uncertainty increases.
- Showed that the proposed **Stochastic Monte Carlo SSM Fusion** produces a calibrated Probability of Near-Miss (PoNM) — a continuous safety score — with graceful degradation under noise, without requiring any training data or environmental metadata.
- Introduced a **unified evaluation pipeline** applying Brier Score, AUROC, Temporal IoU, and TTA comparably to deterministic and probabilistic algorithms.

### 6.2 Practical Implications
- PoNM scores can be directly integrated into ADAS warning thresholds, replacing binary hard-coded TTC limits.
- The simulation framework allows systematic sensitivity studies impossible with naturalistic data (controlled noise injection, scenario scripting).
- The interpretability of SSM-based reasoning (each particle's TTC is directly auditable) is an advantage for regulatory certification of ADAS systems (ISO 21448 SOTIF compliance).

### 6.3 Future Work
1. **Activate 2D-TTC for lateral conflict types** (Lane-Change, Cutoff): route conflict type to appropriate TTC formulation in `SSMCalculator.calculate_ttc_2d()`.
2. **Integrate PET for crossing conflicts** (Broadside, Right-of-Way): `calculate_pet()` is implemented but not yet called in classification logic.
3. **Validate on real-world data**: Import Argoverse-2 conflict resolution dataset (21,000+ annotated interactions; Paper 11) using a new `Sources/data_loader_argoverse.py`.
4. **Behaviour-aware PoNM**: Condition PoNM on detected driver behaviour (defensive/evasive); $PoNM_{\text{behavioral}} = PoNM \times (1 - p_{\text{evasion}})$.
5. **Adaptive threshold selection**: Context-aware threshold multipliers (highway vs. urban intersection) using scenario classification.
6. **Multi-participant conflict chains**: After pairwise SSM evaluation, propagate conflict flags through object pairs to detect secondary near-misses (inspired by Del Re et al., Paper 7).

---

## Appendix Candidates

- **Appendix A**: Full SSM formula derivations (TTC 1D/2D, DRAC, PET, MDR).
- **Appendix B**: Synthetic data generator parameter table (all `SimulationConfig` and `SSMThresholds` values).
- **Appendix C**: Algorithm parameter sensitivity (N-sample sweep for Stochastic predictor: N ∈ {10, 20, 30, 50, 100}).
- **Appendix D**: Full evaluation results table (all scenarios, all metrics, all algorithms).
- **Appendix E**: GUI application screenshot and walkthrough (for reproducibility).

---

## Cross-Cutting Notes for Writing

### Terminology Consistency
| Term in code | Term in paper |
|---|---|
| `NearMissPredictor` | "Rule-Based SSM Algorithm" |
| `StochasticPredictor` | "Stochastic MC-SSM Algorithm" / "Proposed Method" |
| `DistancePredictor` | "Distance Baseline" |
| `PoNM` | "Probability of Near-Miss (PoNM)" |
| `MIXED_NEAR_MISS` | "Mixed-traffic near-miss scenario" |
| `max_confidence` | "PoNM score" (Stochastic) / "rule confidence" (Rule-Based) |
| `t-IoU` | "Temporal Intersection-over-Union (t-IoU)" |

### Key Equations to Typeset
1. PoNM formula (Section 3.5 / Algorithm C)
2. Brier Score (Section 3.6.2)
3. t-IoU (Section 3.6.3)
4. Stochastic sampling distribution (Section 3.5)
5. TTC 1D (Section 3.3)
6. DRAC (Section 3.3)

### Literature References (BibTeX keys to use)
| BibTeX key | Paper |
|---|---|
| `jiao2024unified` | Jiao et al. 2024 (AMAR) — probabilistic SSM |
| `degelder2023prisma` | de Gelder et al. 2023 PRISMA (AAP) |
| `li2021ttcbias` | Li et al. 2021 — 1D vs 2D TTC accuracy |
| `seq2seq2022` | Seq2Seq LSTM trajectory prediction (TITS) |
| `gpr2022` | GPR uncertainty trajectory (TITS) |
| `abdelaty2023survey` | Abdel-Aty et al. 2023 CV safety survey |
| `delre2022multi` | Del Re et al. 2022 — multi-vehicle SSM chains |
| `lipedestrian2022` | Li et al. 2022 — pedestrian probabilistic TTC (TITS) |
| `ttc2d2023` | 2D-TTC lane-change study (AAP) |
| `alhaideri2021` | Al-Haideri 2021 — driver behaviour & thresholds |
| `liconflict2024` | Li et al. 2024 — Argoverse-2 conflict dataset |
| `anowar2021pet` | Anowar et al. 2021 — PET review (AAP) |
