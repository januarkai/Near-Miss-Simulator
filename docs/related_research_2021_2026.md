# Related Research Review (2021–2026)
**Project Context**: Deterministic Near-Miss Prediction Simulator using BEV + SSMs
*Compiled: February 22, 2026*

---

## Overview

This document reviews 10 closely related research works published between 2021 and 2026 from IEEE Transactions on Intelligent Transportation Systems, Accident Analysis & Prevention, Analytic Methods in Accident Research, and arXiv preprints. Each paper is analyzed for its core contribution, methodology, limitations, and direct relevance to this simulator project.

---

## Paper 1

**Title**: A Unified Probabilistic Approach to Traffic Conflict Detection
**Authors**: Yiru Jiao, Simeon C. Calvert, Sander van Cranenburgh, Hans van Lint
**Year**: 2024 (updated December 2024)
**Published in**: *Analytic Methods in Accident Research* (Elsevier)
**arXiv**: [2407.10959](https://arxiv.org/abs/2407.10959)
**DOI**: 10.1016/j.amar.2024.100369

### What They Did
This paper is arguably the most directly relevant work to this project's novel contribution. The authors argue that existing SSM methods are fundamentally broken because each one (TTC, DRAC, PET) was designed for a specific interaction type (e.g., car-following, side-swiping, path-crossing) and requires **different thresholds for different traffic conditions**. This inconsistency makes cross-scenario comparison impossible.

Their solution is a **unified probabilistic framework** that reframes traffic conflicts as **context-dependent extreme events** of road user interactions. Instead of a single threshold, they:
1. Model interaction contexts using statistical learning (capturing motion states, environment conditions, participant characteristics).
2. Infer **proximity distributions** from road user pairs.
3. Assess **extreme collision risk** as the tail probability of those distributions — similar in spirit to Extreme Value Theory.

They test on real-world trajectory datasets and demonstrate the approach generalizes across distinct datasets and traffic environments, covering a broad range of conflict types, and capturing the long-tailed distribution of conflict intensity.

### Core Formulation
The approach defines a conflict as occurring when the proximity between road users is in the **extreme tail** of the interaction distribution:
$$P(\text{conflict}) = P(proximity < \tau_{context})$$
where $\tau_{context}$ is not a fixed global threshold but is **learned from data** for each context.

### Key Findings
- Traditional SSMs fail because their thresholds were calibrated on specific road types and interaction patterns
- The proposed framework generalizes well: trained on one dataset, tested on another with no retraining needed
- Effective for collision warnings in autonomous driving contexts
- Captures long-tailed distributions that deterministic binary systems miss entirely

### Limitations Acknowledged
- Requires real-world trajectory data to learn context distributions (not applicable purely in simulation)
- Computational cost of statistical learning tasks is higher than simple threshold checks
- The "context" representation itself is a design choice that can introduce bias

### Relevance to This Project
**Extremely high.** This paper directly attacks the same "binary rigidity" gap identified in this project's `gap_analysis_and_novelty.md`. The unified framework is the conceptual ground truth that both this project's Rule-Based SSM and Stochastic Monte Carlo algorithms are approximating. Key takeaway: the authors show that probabilistic framing of conflicts outperforms deterministic threshold-based methods — validating the thesis direction.

**What this project does differently**: This project does *not* require real-world data; it works in a synthetic simulation context. The Monte Carlo SSM Fusion approach is computationally cheaper (no statistical learning required) and produces an interpretable PoNM score. The thesis can cite this paper to justify why the probabilistic direction is the right one.

---

## Paper 2

**Title**: PRISMA: A Novel Approach for Deriving Probabilistic Surrogate Safety Measures for Risk Evaluation
**Authors**: Erwin de Gelder, Kingsley Adjenughwure, Jeroen Manders, Ron Snijders, Jan-Pieter Paardekooper, Olaf Op den Camp, Arturo Tejada, Bart De Schutter
**Year**: 2023
**Published in**: *Accident Analysis & Prevention* (Elsevier)
**arXiv**: [2303.07891](https://arxiv.org/abs/2303.07891)
**DOI**: 10.1016/j.aap.2023.107273

### What They Did
PRISMA (Probabilistic RISk Measure derivAtion) is a method framework for deriving SSMs that output **real-time crash probability** rather than a deterministic severity score. The core insight is that traditional SSMs rely on rigid assumptions about future trajectory evolution (constant velocity, no lane change, etc.), which makes them unreliable when those assumptions are wrong.

**Architecture of PRISMA**:
1. Use a **data-driven approach** to predict the possible future trajectories of each traffic participant (generating a trajectory distribution, not a single prediction).
2. Run Monte Carlo simulations over this trajectory distribution to calculate the probability that a crash occurs.
3. Combine the simulation results with a **regression model** to obtain a real-time risk estimate without re-running the full simulation at every frame.

The paper applies PRISMA specifically to **longitudinal traffic interactions** (rear-end scenarios) as a demonstration case and shows that the derived SSM matches expected risk trends.

### Key Findings
- The derived probabilistic SSM matches expected risk trends (higher risk when following distance is smaller and relative velocity is larger)
- The regression model wrapper enables real-time inference from the Monte Carlo precomputation
- There is no known "ground truth risk" — validation relies on behavioral benchmarking against expected trends, not crash labels
- Future work identified: lateral conflicts, vulnerable road user interactions

### Limitations Acknowledged
- Currently limited to longitudinal interactions only (rear-end)
- Regression model is trained on the specific traffic context used in training
- No objective ground truth risk makes cross-method comparison difficult
- Computationally expensive during the precomputation phase

### Relevance to This Project
**Very high.** PRISMA is conceptually the closest academic precedent to this project's `StochasticPredictor`. Both:
- Replace a single trajectory prediction with a distribution of trajectories
- Use Monte Carlo sampling
- Output a probability of risk rather than a binary flag

**Key difference**: PRISMA uses a pre-learned regression model to cache Monte Carlo results for real-time use. This project runs Monte Carlo sampling live at each frame (N=30 samples), which is simpler but more computationally direct.

**Thesis positioning**: This project can be framed as a **lightweight SimSafe extension** of PRISMA: applying the PRISMA philosophy to the simulation context, with the synthetic data generator providing the uncertainty model directly (instead of needing historical data to estimate it). The explicit connection to PRISMA strengthens the novelty claim.

---

## Paper 3

**Title**: Beyond 1D and Oversimplified Kinematics: A Generic Analytical Framework for Surrogate Safety Measures
**Authors**: Sixu Li, Mohammad Anis, Dominique Lord, Hao Zhang, Yang Zhou, Xinyue Ye
**Year**: 2023–2024 (published May 2024)
**Published in**: *eess.SY / Systems and Control* (arXiv, submitted to peer review)
**arXiv**: [2312.07019](https://arxiv.org/abs/2312.07019)

### What They Did
This paper is a systematic critique of the status quo in SSM calculation: most practical implementations — including this project's `SSMCalculator` — use **1D (longitudinal-only) kinematic models**. The authors demonstrate that this introduces large errors and propose a **generic analytical framework** extending SSMs to multi-dimensional, high-fidelity kinematics.

**Framework Components**:
1. A **generic vehicle movement model** parameterized by dimensionality and fidelity (1D, 2D, 3D)
2. A **collision criterion** based on spatial overlap (bounding-box intersection, not center-to-center distance)
3. An algorithm to find the **minimum TTC** over all non-negative time points, for any movement model combination

**Critical Finding (Quantified Error)**:
- Using 1D SSMs (current standard, including in this project) vs. 3D SSMs:
  - **Non-critical TTC values** (> 1.5s): Error up to **300%**
  - **Critical TTC values** (< 1.5s, near-miss region): Error ~**20%**
- This means the current project's 1D/simplified TTC calculator is acceptable for near-miss detection (20% error at critical range) but would be unreliable for safe distance estimation.

### Key Findings
- 1D SSMs are systematically wrong for lateral/turning scenarios
- Bounding-box-based collision detection is significantly more accurate than center-point-based
- The framework can accommodate CTRV model (constant turn rate with velocity) and higher-order models through linearization
- Practical validation confirms accuracy in dynamic real-world environments

### Limitations Acknowledged
- Computational cost scales with model dimensionality
- Linearization approximation introduces small errors in highly non-linear motion
- The framework itself is analytical, not a real-time system (implementation requires engineering effort)

### Relevance to This Project
**High.** This directly addresses `Algorithm/ssm_calculator.py`:
- `calculate_ttc()` is a pure 1D model (object ahead, same lane check) — confirmed valid for rear-end but fundamentally wrong for lateral/crossing scenarios
- `calculate_ttc_2d()` exists in the code but is not the primary method used
- The project's `ConflictType` detection (BROADSIDE, RIGHT_OF_WAY) requires 2D SSMs to be accurate

**Actionable**: For the BROADSIDE and CROSSING conflict types, switching from the 1D TTC to the existing `calculate_ttc_2d()` method would bring the simulator closer to the standard demonstrated here. The paper also validates that bounding-box collision detection (which this project already implements in `TrackedObject.get_corners()`) is the right approach.

---

## Paper 4

**Title**: Trajectory Prediction for Vehicle Conflict Identification at Intersections Using Sequence-to-Sequence Recurrent Neural Networks
**Authors**: Amr Abdelraouf, Mohamed Abdel-Aty, Zijin Wang, Ou Zheng
**Year**: 2022
**Published in**: *Submitted to IEEE Transactions on Intelligent Transportation Systems*
**arXiv**: [2210.08009](https://arxiv.org/abs/2210.08009)

### What They Did
This paper bridges trajectory prediction (ML side) with surrogate safety measures (physics side). The authors argue that **prediction-based conflict indicators** (where TTC is computed from a predicted future trajectory) are more useful than **past-trajectory-based** indicators (where TTC is computed from extrapolated current states). However, their accuracy depends entirely on the quality of the trajectory predictor.

**Method**:
- Built a **Sequence-to-Sequence LSTM** (Encoder-Decoder RNN architecture) trained on the **CitySim Dataset**
- Predicted both future **positions (x, y)** and **heading angles** up to 3 seconds ahead
- Used the predicted bounding boxes (not center points) to compute TTC
- Compared against: Constant Velocity model, Social Force model, LSTM without heading prediction

**Key Findings**:
- Seq2Seq LSTM outperforms all baselines for conflict identification at intersections
- **Bounding-box TTC vs. center-point TTC**: Center-point approach frequently **fails to identify conflicts or underestimates severity** — conflicting with what the center-point method shows
- Heading prediction is critical: without it, bounding-box TTC is no more accurate than center-point
- 3-second prediction horizon is sufficient for near-miss detection at urban intersections

### Limitations Acknowledged
- Trained specifically on CitySim dataset — generalization to other environments untested
- High computational cost of Seq2Seq model vs. constant velocity
- Requires labeled trajectory data which is costly to acquire

### Relevance to This Project
**Moderate-High.** This paper validates two design choices already in this project:
1. **Bounding-box based collision detection** — implemented in `TrackedObject.get_corners()` and the trajectory predictor
2. **3-second prediction horizon** — default `prediction_horizon = 3.0s` in `SimulationConfig`

But it exposes a gap: the project uses a **Constant Velocity Model** (`ConstantVelocityModel`), which is the weakest baseline shown in this paper. For the thesis, this motivates either:
- Implementing a simple LSTM-based trajectory predictor (high effort)
- Justifying the CV model choice by constraining to scenarios where it is adequate (highway following) and the Monte Carlo perturbations model the uncertainty of deviations

---

## Paper 5

**Title**: Connecting Surrogate Safety Measures to Crash Probability via Causal Probabilistic Time Series Prediction
**Authors**: Jiajian Lu, Offer Grembek, Mark Hansen
**Year**: 2022
**Published in**: *arXiv cs.LG / cs.AI*
**arXiv**: [2210.01363](https://arxiv.org/abs/2210.01363)

### What They Did
This paper addresses a fundamental validation problem in traffic safety research: **how do you know if your SSM is actually predictive of real crashes?** The authors propose a causal probabilistic framework using **Transformer Masked Autoregressive Flow (Transformer-MAF)** to connect SSM time series to crash probability.

**Method**:
- Input: sequences of speed, acceleration, and TTC
- Model: Transformer-MAF learns the **joint probability density function** of these variables over time
- Output: conditional crash probability (given the current sequence, what is $P(\text{crash})$?)
- The autoregressive structure mimics the **causal chain**: condition → action → outcome

This allows:
1. Estimating the distribution of counterfactual scenarios ("what if the driver braked earlier?")
2. Calculating whether a given evasive action was necessary and sufficient
3. Connecting SSM values at time $t$ to the actual crash outcome

### Key Findings
- The model generates accurate and calibrated probability density functions for both conflict and normal interaction contexts
- Conditional crash probability shows clear effectiveness of evasive actions in avoiding crashes (counterfactual reasoning)
- TTC sequences alone are not sufficient — acceleration sequences add critical information about driver intent

### Limitations Acknowledged
- Requires historical crash data (or near-crash naturalistic data) for training
- Transformer-MAF is computationally expensive
- The causal interpretation assumes no hidden confounders, which is difficult to guarantee

### Relevance to This Project
**Medium-High.** The core problem this paper solves — connecting SSM values to crash probability — is exactly what this project's thesis addresses via the Brier Score evaluation metric. Specifically:
- The causal chain (condition → action → outcome) maps to: (object state → near-miss detection algorithm → near-miss label)
- The conditional crash probability framework validates why Brier Score is the right evaluation metric for comparing deterministic vs. probabilistic algorithms
- The finding that "TTC sequences alone are insufficient" supports implementing acceleration-based DRAC alongside TTC in this project

**Actionable**: The thesis can cite this paper to justify the use of **TTC + DRAC + MDR fusion** (rather than TTC alone), as this paper empirically shows that multi-feature SSM sequences are necessary for probabilistic accuracy.

---

## Paper 6

**Title**: Advances and Applications of Computer Vision Techniques in Vehicle Trajectory Generation and Surrogate Traffic Safety Indicators
**Authors**: Mohamed Abdel-Aty, Zijin Wang, Ou Zheng, Amr Abdelraouf
**Year**: 2023
**Published in**: *Accident Analysis & Prevention*
**arXiv**: [2303.15231](https://arxiv.org/abs/2303.15231)
**DOI**: 10.1016/j.aap.2023.107191

### What They Did
This is a **comprehensive survey paper** covering the entire pipeline from raw video to SSM-based safety analysis. It is not a single novel algorithm but a systematic review of the state of the art (up to early 2023) in:
1. Vehicle detection models (YOLO, Faster-RCNN, etc.)
2. Multi-object tracking algorithms (DeepSORT, ByteTrack, etc.)
3. Video preprocessing and trajectory extraction
4. SSM calculation from extracted trajectories
5. Practical issues: occlusion, camera distortion, calibration errors

### Key Survey Findings
- **Detection → Tracking → SSM** pipeline introduces cumulative errors; each stage can degrade SSM quality
- **Most common SSMs in CV-based systems**: TTC and DRAC (longitudinal), PET (crossing), spacing/gap headway (following)
- **Biggest practical issue**: Inaccurate vehicle geometry (width, length estimation) significantly distorts TTC and DRAC values
- **Emerging trend (2022–2023)**: BEV transformation + aerial/drone video is replacing roadside cameras because BEV eliminates perspective distortion and simplifies SSM calculation
- **Gap identified**: Few works combine end-to-end learning (detection to conflict prediction) — most still use modular pipelines

### Relevance to This Project
**Moderate but strategically important.** This paper validates the core architectural choice of this project:
- Using **BEV directly** (without image processing pipeline) is the correct epistemological choice — it removes accumulated errors from the detection/tracking stages
- The paper's identification of "accurate vehicle geometry" as critical directly validates why `TrackedObject` stores explicit `length` and `width` fields, and why the simulator uses bounding-box collision detection
- The **drone/aerial BEV trend** (2022–2023) matches this project's ego-centric BEV frame concept

**For thesis positioning**: This survey can be cited in the "Related Work on SSM" section to justify why this project operates at the BEV trajectory level rather than the raw video level.

---

## Paper 7

**Title**: Method for Comparison of Surrogate Safety Measures in Multi-Vehicle Scenarios
**Authors**: Enrico Del Re, Cristina Olaverri-Monreal
**Year**: 2023
**Published in**: *arXiv cs.RO (submitted to IEEE Intelligent Vehicles Symposium)*
**arXiv**: [2304.08998](https://arxiv.org/abs/2304.08998)

### What They Did
This short paper (6 pages) addresses a specific gap: while pairwise SSM analysis (one ego + one object) is well established, **multi-vehicle interactions** involving three or more participants remain poorly understood. The authors study the specific case of a **three-vehicle lane change** on a highway: ego vehicle + lead vehicle + lane-changing vehicle.

**Method**:
- Compute SSM values (TTC, DRAC) for all *pairwise* combinations in a 3-vehicle interaction
- Compare how the safety distances shift when the lane change begins
- Statistical analysis of when the primary conflict (lead vs. lane-changer) creates secondary risk (ego vs. lead)

**Key Findings**:
- In 3-vehicle lane changes, the primary conflict (lane-changer vs. lead) causes the **lead vehicle to brake**, which then creates a **secondary rear-end conflict** with the ego vehicle
- Standard pairwise SSM analysis misses this **conflict propagation effect**
- The safety-critical moment for the ego is often *after* the primary conflict resolves (i.e., after the lane change completes) — a timing issue that the current approach misses

### Limitations Acknowledged
- Only studies one specific multi-vehicle scenario type
- Does not propose a new algorithm — purely analytical/measurement study
- Small sample size simulation study

### Relevance to This Project
**Medium.** This paper directly challenges the **pairwise analysis** used in this project's `predict_frame()` method. Currently, each `TrackedObject` is evaluated independently against the ego — there is no mechanism to detect conflict propagation chains.

In the project's `ConflictType.LANE_CHANGE` detection, an adjacent vehicle cutting in might cause further downstream effects not currently captured. The paper suggests this is a meaningful gap.

**Actionable for thesis**: The thesis can acknowledge this as a **future work item**: extending the pairwise SSM framework to multi-participant interaction modeling. It also suggests that `MIXED_NEAR_MISS` scenarios should include multi-vehicle chains, not just isolated pairwise interactions.

---

## Paper 8

**Title**: A Probabilistic Framework for Estimating the Risk of Pedestrian-Vehicle Conflicts at Intersections
**Authors**: Pei Li, Huizhong Guo, Shan Bao, Arpan Kusari
**Year**: 2022
**Published in**: *IEEE Transactions on Intelligent Transportation Systems*
**arXiv**: [2207.14145](https://arxiv.org/abs/2207.14145)
**DOI**: 10.1109/TITS.2023.3296567

### What They Did
This paper proposes a probabilistic SSM framework specifically for **pedestrian-vehicle conflicts at intersections**, addressing two key failures of constant-velocity-based SSMs when applied to pedestrians:
1. Pedestrians have highly irregular, non-constant velocities (stopping, accelerating, reversing)
2. Drivers execute **evasive maneuvers** (braking, swerving) that constant-velocity models cannot represent

**Method**:
- **Gaussian Process Regression (GPR)**: Predicts pedestrian trajectory as a Gaussian distribution $\mathcal{N}(\mu(t), \sigma^2(t))$, providing both predicted position and associated uncertainty
- **Random Forest Classifier**: Classifies the driver's likely maneuver type (maintain speed, brake, swerve) based on current state history
- Combined to compute: $P(\text{conflict}) = P(pedestrian \cap vehicle \neq \emptyset | \text{maneuver})$
- Real-world LiDAR dataset from an intersection used for validation

**Key Findings**:
- The framework identifies **all** pedestrian-vehicle conflicts in the test set (Recall = 1.0)
- Compared to standard TTC: proposed framework gives more **stable risk estimation** (no cliff-edge jumps)
- Captures evasive maneuvers — TTC remains high (Safe) even when a pedestrian walks into the road, as long as the driver brakes appropriately
- Does not require expensive GPU computation; real-time capable

### Limitations Acknowledged
- Trained on LiDAR data at one specific intersection — spatial generalization not tested
- Random Forest maneuver classifier is a simplified model (doesn't capture full driver diversity)
- GPR scales poorly with amount of historical trajectory data

### Relevance to This Project
**High.** This paper provides strong empirical evidence for why **constant-velocity assumptions in SSM calculation are wrong for pedestrian interactions**. In this project:
- `ScenarioType.CROSSING_PEDESTRIAN` uses a pedestrian with constant-velocity assumptions
- The `SSMCalculator` uses the same 1D/2D TTC formulas for pedestrians as for vehicles

The Gaussian Process approach used here is essentially the "data-driven" equivalent of this project's Monte Carlo perturbation approach. Both methods use a distribution over future trajectories instead of a single one. The main difference is that GPR is principled (using learned covariance functions) while Monte Carlo uses a hand-tuned Gaussian with fixed `pos_uncertainty_std`.

**Actionable**: The thesis can position the Stochastic Monte Carlo predictor as a computationally simpler approximation of the GPR-based probabilistic framework — trading principled covariance for computational simplicity and interpretability.

---

## Paper 9

**Title**: Modeling Driver's Evasive Behavior During Safety-Critical Lane Changes: Two-Dimensional Time-to-Collision and Deep Reinforcement Learning
**Authors**: Hongyu Guo, Kun Xie, Mehdi Keyvan-Ekbatani
**Year**: 2022
**Published in**: *Accident Analysis & Prevention*
**arXiv**: [2209.15133](https://arxiv.org/abs/2209.15133)
**DOI**: 10.1016/j.aap.2023.107063

### What They Did
This paper proposes **2D-TTC** as a new SSM specifically designed for lane-change conflicts, then uses it alongside a **Deep Deterministic Policy Gradient (DDPG)** reinforcement learning agent to model and reproduce evasive driving behavior.

**2D-TTC Definition**:
$$TTC_{2D} = \sqrt{TTC_x^2 + TTC_y^2}$$
where $TTC_x$ = longitudinal TTC, $TTC_y$ = lateral TTC computed separately, then combined geometrically. This captures the combined risk from both dimensions simultaneously.

**Methodology**:
- Large-scale connected vehicle naturalistic data (Safety Pilot Model Deployment, 2012–2014, Michigan)
- 2D-TTC used to identify safety-critical lane-change situations in the dataset
- DDPG agent trained to reproduce the human driver's **longitudinal and lateral responses** (acceleration, steering) during these critical situations
- Validation: 2D-TTC values correlated with archived crashes (high correlation = good proxy for real danger)

**Key Findings**:
- 2D-TTC detected more lane-change conflicts than 1D TTC (both lateral and longitudinal components matter)
- High correlation between 2D-TTC-detected conflicts and real crash records — validates 2D-TTC as reliable SSM
- DDPG successfully replicates both longitudinal and lateral evasive behaviors
- Standard 1D TTC misses pure lateral lane-change conflicts where $TTC_x$ is very large but $TTC_y$ is critical

### Limitations Acknowledged
- Connected vehicle data only (not BEV — different sensor type and frame of reference)
- DDPG model is trained for specific highway context
- 2D-TTC is empirically defined, lacks theoretical grounding compared to the Li et al. generic framework

### Relevance to This Project
**Very high for the `LANE_CHANGE` and `CUTOFF` conflict types.** The project's current `calculate_ttc()` is purely longitudinal. For lane changes:
- `calculate_ttc_2d()` already exists in the code but only computes a combined Euclidean approach
- The paper proposes the more principled $TTC_{2D} = \sqrt{TTC_x^2 + TTC_y^2}$ formulation

**Actionable**: Implement the 2D-TTC formulation from this paper in `ssm_calculator.py` for the LANE_CHANGE and CUTOFF conflict types. The paper also provides validated threshold values: $TTC_{2D} < 1.5s$ for critical, $< 3.0s$ for warning in lane-change scenarios.

---

## Paper 10

**Title**: Latent Class Logit Kernel Framework for Surrogate Safety: Identifying Behavioural Thresholds through Conflict Indicator Profiles
**Authors**: Rulla Al-Haideri, Changhe Liu, Karim Ismail, Bilal Farooq, Chi Zhang
**Year**: 2025
**Published in**: *arXiv physics.soc-ph (preprint)*
**arXiv**: [2510.12012](https://arxiv.org/abs/2510.12012)

### What They Did
This 2025 paper attacks the threshold selection problem head-on: how do you choose the right value for `ttc_near_miss = 1.5s`? The answer, until now, has been expert judgment supported by empirical crash studies. This paper proposes to **derive thresholds from observed driver behavior** using a **Latent Class Logit Kernel (LC-LK) model**.

**Core Idea**:
- Drivers can be classified into **latent behavioral classes**: "routine drivers" (comfortable at high risk situations) and "defensive drivers" (already reacting at lower risk)
- As conflict indicators like TTC decrease, the probability of observing a **defensive maneuver** increases
- The threshold should be the TTC value where the probability of defensive response crosses a meaningful level (e.g., inflection point in the logistic curve)

**LC-LK Model**:
- Captures **inter-class heterogeneity**: different drivers have different response thresholds
- Captures **intra-class correlation**: same driver may react differently to spatial alternatives at the same risk level
- Applied to naturalistic roundabout trajectories

**Key Findings**:
- **TTC threshold**: Stable across drivers at **0.8–1.1 seconds** — converges with existing expert-based literature
- **MTTC2 (a complex 2D TTC measure)**: Highly unstable estimates (e.g., 34s vs. expected ~3–5s) — suggests drivers **cannot cognitively process complex multi-dimensional conflict indicators**
- EVT-based thresholds and behavioral thresholds complement each other but are not identical
- Even in free-flow conditions, drivers maintain a **baseline caution level** (non-zero membership in defensive class)

### Limitations Acknowledged
- Applied only to roundabouts — different threshold values may apply to highways or intersections
- Latent class model requires large naturalistic datasets
- Logistic shape assumption may not hold in all traffic environments

### Relevance to This Project
**High for threshold calibration.** This paper provides the most principled justification in recent literature for specific SSM threshold values:
- The TTC near-miss threshold of 0.8–1.1s (behavioral) aligns with this project's `ttc_near_miss = 1.0s` — validating that configuration
- The `ttc_warning = 2.0s` threshold is higher than the behavioral threshold, which is intentional (warning before the critical zone)
- The instability of complex multi-dimensional SSMs supports keeping the system's core SSMs as interpretable as possible (TTC, DRAC, MDR) rather than adding complex derived measures

**For thesis positioning**: The project's threshold choices can be cited alongside this paper as behaviorally grounded rather than arbitrary, strengthening the scientific rigor of the experimental setup.

---

## Paper 11

**Title**: A Conflict Resolution Dataset Derived from Argoverse-2: Analysis of the Safety and Efficiency Impacts of Autonomous Vehicles at Intersections
**Authors**: Guopeng Li, Yiru Jiao, Simeon C. Calvert, J.W.C. van Lint
**Year**: 2023
**Published in**: *arXiv cs.RO / eess.SY*
**arXiv**: [2308.13839](https://arxiv.org/abs/2308.13839)

### What They Did
This paper provides **open real-world data** and analysis comparing AV-involved vs. AV-free conflict resolution at intersections. The dataset (5,000+ AV conflicts + 16,000+ human-only conflicts from Argoverse-2) represents one of the largest publicly available annotated conflict datasets.

**Methodology**:
- Data pipeline: select AV interaction scenarios from Argoverse-2, apply trajectory correction (smoothing, error rectification), annotate conflict resolution regime
- SSM evaluation: TTC, DRAC, headway, and a novel **efficiency measure** (completion time vs. optimal unconstrained)

**Key Findings**:
- Human drivers show **similar safety performances** when interacting with AVs vs. other humans (AVs don't scare people into poor decisions)
- **Pedestrians show more diverse reactions** to AVs (some freeze, some ignore, some slow down) — heterogeneous and hard to predict
- AV safety-prior behavior reduces average efficiency by **8.6%** compared to human-only conflict resolution
- This dataset is publicly available: [GitHub link](https://github.com/RomainLITUD/conflict_resolution_dataset)

### Limitations Acknowledged
- Argoverse-2 was recorded in specific US cities — geographic bias
- AV and human-driver interactions may differ from fully human traffic
- SSMs applied are standard deterministic measures, not probabilistic

### Relevance to This Project
**Moderate but practical.** This paper provides:
1. **Public annotated conflict data** that could be used to validate this project beyond synthetic data
2. Evidence that **pedestrian behavior next to AVs is non-standard** — supporting the project's heterogeneous scenario types (CROSSING_PEDESTRIAN)
3. The efficiency-safety tradeoff finding (8.6% efficiency loss) could frame the thesis argument: not all "safe" behaviors are optimal — near-miss prediction algorithms should balance sensitivity and false alarm rate

**Actionable**: Import and test this project's algorithm on the Argoverse-2 derived dataset (after implementing a CSV importer for the dataset format) as an external validation step.

---

## Paper 12

**Title**: Trajectory-Based Real-Time Pedestrian Crash Prediction at Intersections: A Novel Non-Linear Link Function for Block Maxima Led Bayesian GEV Framework Addressing Heterogeneous Traffic Condition
**Authors**: Parvez Anowar, Nazmul Haque, Md Asif Raihan, Md Hadiuzzaman
**Year**: 2025
**Published in**: *arXiv stat.AP (preprint, under peer review)*
**arXiv**: [2510.12963](https://arxiv.org/abs/2510.12963)

### What They Did
This 2025 preprint addresses crash prediction specifically in **heterogeneous, non-lane-based traffic** (South/Southeast Asian traffic conditions where vehicles don't follow lanes strictly). The paper extends the Extreme Value Theory (EVT) approach to crash risk using:
- **Post-Encroachment Time (PET)** as the surrogate safety measure
- **Bayesian Generalized Extreme Value (GEV) framework** using block maxima approach
- **Non-linear link functions** for the GEV parameters (instead of the standard linear assumption)
- **Markov Chain Monte Carlo (MCMC)** sampling for Bayesian estimation

A new metric: **Modified Crash Risk (MRC)** that accounts for **habitual risk-taking behavior** (pedestrians in congested mixed traffic routinely accept smaller gaps, so raw PET values overestimate risk in those contexts).

**Key Findings**:
- Non-linear link function models significantly outperform linear counterparts (lower DIC)
- Pedestrian speed has a **negative** relationship with crash risk (faster pedestrians cross more decisively)
- Vehicle speed and flow **positively** contribute to crash risk
- MRC metric reduces overestimation and achieves **93% confidence in crash predictions**

### Limitations Acknowledged
- Specific to heterogeneous non-lane-based traffic (limitations in applying to standard lane-based highway contexts)
- MCMC is computationally intensive
- Single intersection study

### Relevance to This Project
**Moderate.** Most directly relevant to the project's pedestrian scenario types:
- `CROSSING_PEDESTRIAN` and `NEAR_MISS_BROADSIDE` scenarios involve pedestrians in the BEV space
- The finding that **PET is a good SSM for crossing scenarios** validates that `ssm_calculator.calculate_pet()` should be given more prominence for BROADSIDE and crossing conflicts (currently PET is implemented but not actively used in the classification logic)
- The **MRC concept** (behavior-normalized risk) connects to this project's `confidence` score — accounting for the fact that not all SSM threshold crossings represent the same danger level

---

## Summary Table

| # | Paper | Year | Venue | Core Relevance |
|---|---|---|---|---|
| 1 | Unified Probabilistic Conflict Detection (Jiao et al.) | 2024 | AMAR (Elsevier) | Validates probabilistic SSM direction; unified framework |
| 2 | PRISMA (de Gelder et al.) | 2023 | AAP (Elsevier) | Direct precedent for StochasticPredictor |
| 3 | Beyond 1D SSMs (Li et al.) | 2024 | eess.SY | Quantifies 1D TTC error; validates bounding-box approach |
| 4 | Seq2Seq RNN Conflict (Abdelraouf et al.) | 2022 | IEEE T-ITS | Validates 3s horizon; bounding box vs center point |
| 5 | SSM-to-Crash-Probability (Lu et al.) | 2022 | arXiv cs.LG | Validates Brier Score; multi-feature SSM necessity |
| 6 | CV Techniques for SSM Survey (Abdel-Aty et al.) | 2023 | AAP | Validates BEV approach; geometry accuracy importance |
| 7 | Multi-Vehicle SSM Comparison (Del Re et al.) | 2023 | arXiv cs.RO | Gap: multi-vehicle interaction propagation |
| 8 | Probabilistic Pedestrian-Vehicle (Li et al.) | 2022 | IEEE T-ITS | GPR ~ Monte Carlo; pedestrian constant-velocity flaw |
| 9 | 2D-TTC & DDPG Lane Change (Guo et al.) | 2022 | AAP | 2D-TTC formulation for LANE_CHANGE/CUTOFF types |
| 10 | Behavioural Thresholds LC-LK (Al-Haideri et al.) | 2025 | arXiv phys.soc | Empirical threshold validation (TTC=0.8–1.1s) |
| 11 | Argoverse-2 Conflict Dataset (Li et al.) | 2023 | arXiv cs.RO | Open validation dataset; AV-human interaction insights |
| 12 | Bayesian GEV Pedestrian Risk (Anowar et al.) | 2025 | arXiv stat.AP | PET for crossing; behavior-normalized risk |

---

## Cross-Cutting Themes (2021–2026)

Reading all 12 papers together, five major trends define the 2021–2026 research landscape:

### Theme 1: The Death of Fixed Thresholds
Papers 1, 10, and 12 all independently conclude that **fixed global thresholds for SSMs are scientifically indefensible**. The field is moving toward data-driven or behavioral thresholds that adapt to traffic context, road type, and driver population. This is the central scientific challenge that this project's Monte Carlo approach partially addresses (by producing a probability rather than a binary flag).

### Theme 2: Probabilistic Frameworks Are Winning
Papers 1, 2, 5, 8, and 12 all propose probabilistic extensions to deterministic SSMs. The convergence on this direction across IEEE T-ITS, Accident Analysis & Prevention, and Analytic Methods in Accident Research suggests it is the **consensus direction for the field**. This validates this thesis's core novel contribution.

### Theme 3: The 1D TTC Must Die
Papers 3, 9, and 4 all point to failures of 1D (longitudinal-only) TTC. Paper 3 quantifies the error (up to 300% for non-critical values). The field is converging on 2D multi-object bounding-box approaches. This project's `calculate_ttc_2d()` is in the right direction but is not used as the primary method.

### Theme 4: BEV + Real-World Trajectory Data Is the Standard
Papers 6, 11, and 4 all confirm that BEV trajectory analysis is the appropriate framework for SSM-based safety research. The transition from roadside cameras → aerial cameras → direct trajectory datasets (Argoverse-2, CitySim) mirrors this project's choice to work directly at the BEV trajectory level with synthetic data.

### Theme 5: Pedestrian Heterogeneity Is Unsolved
Papers 8 and 12 both demonstrate that pedestrian behavior violates every assumption in standard SSM frameworks (constant velocity, lane-following, rational evasion). Pedestrian scenarios remain an open research challenge and a differentiating opportunity.

---

# Research Plan Suggestions

Based on the literature review above and the current state of the project, the following research plan is proposed. Items are ordered by estimated scientific impact and implementation difficulty.

---

## Phase 1: Strengthen the Existing Comparison (Short-Term, 2–4 weeks)

### 1.1 Implement 2D-TTC as the Primary SSM for Lateral Conflict Types
**Motivation**: Paper 3 (Li et al.) shows 1D TTC introduces up to 300% error for non-critical values. Paper 9 (Guo et al.) provides the validated formula:
$$TTC_{2D} = \sqrt{TTC_x^2 + TTC_y^2}$$

**Implementation**:
- Modify `SSMCalculator` to route conflict type → TTC formula:
  - `REAR_END` → existing `calculate_ttc()` (1D, valid)
  - `LANE_CHANGE`, `CUTOFF` → new $TTC_{2D}$ formulation
  - `BROADSIDE`, `RIGHT_OF_WAY` → existing `calculate_ttc_2d()` (2D with trajectory intersection)
- Update thresholds: Paper 9 indicates $TTC_{2D,critical} = 1.5s$, $TTC_{2D,warning} = 3.0s$ for lane-change contexts

**Expected outcome**: More accurate near-miss detection for lateral scenarios; reduced false negatives in LANE_CHANGE and CUTOFF types.

### 1.2 Activate PET for Crossing Conflicts
**Motivation**: Paper 12 (Anowar et al.) confirms PET is the appropriate SSM for crossing/broadside scenarios. `calculate_pet()` is implemented but not used in `_classify_near_miss()`.

**Implementation**:
- Add PET to the near-miss classification logic for `BROADSIDE` and `RIGHT_OF_WAY` conflict types
- Use PET threshold: `pet_near_miss = 0.5s` (already defined in `SSMThresholds`)
- Store ego trajectory in `FrameData` (or compute within the predictor) to enable PET calculation

**Expected outcome**: Better coverage of crossing-type near-misses; reduced false negatives in intersection-like scenarios.

### 1.3 Fix Ground Truth Tagging in Data Generator
**Motivation**: Identified in `docs/evaluation_theory_plan.md` and confirmed by Papers 1 and 11. Standard scenarios don't tag `is_risk_object=True`, breaking frame-level evaluation.

**Implementation**:
- In `data_generator.py`, explicitly set `is_risk_object=True` on the primary risk object in all scenario types
- Derive ground truth events from physics (TTC < 1.5s check) rather than fixed time windows
- This unblocks AUROC, t-IoU metrics, and frame-level F1 calculation

---

## Phase 2: Validate Against External Data (Medium-Term, 1–2 months)

### 2.1 Implement Argoverse-2 Data Importer
**Motivation**: Paper 11 (Li et al.) provides an open, labeled conflict dataset with 21,000+ annotated interactions. Testing the project's algorithm on this real-world data would dramatically strengthen the thesis from a "simulation-only" study to a "simulation + real validation" study.

**Implementation**:
- Write a new `Sources/data_loader_argoverse.py` that reads the conflict resolution dataset format and produces `FrameData` objects
- Convert Argoverse-2 coordinate frame to ego-centric BEV frame
- Run both Rule-Based SSM and Stochastic predictor on the dataset
- Report Precision/Recall/F1/Brier Score against the annotated labels

**Expected outcome**: External validation claim; direct comparison with the paper's own SSM results.

### 2.2 Implementing the Accuracy-Robustness Curve (Brier Score vs. Noise Level)
**Motivation**: `comparable_evaluation_metrics.md` defines this metric. Papers 1 and 2 implicitly require it (probabilistic methods are only "better" when noise is present).

**Implementation**:
- Add a `noise_multiplier` parameter to `SyntheticDataGenerator` 
- Run the full evaluation pipeline at noise levels: `σ ∈ {0.5, 1.0, 2.0, 4.0, 8.0}` (`position_noise_std` values)
- Plot: Rule-Based F1 vs. σ; Stochastic Brier Score vs. σ; Stochastic F1 at threshold vs. σ
- Use `experiments/robustness_study.py` as the starting scaffold

**Expected outcome**: The key thesis result: Stochastic algorithm degrades gracefully with noise while Rule-Based shows brittle cliff-edge drop.

---

## Phase 3: Novel Contribution Extension (Long-Term, 2–3 months)

### 3.1 Behavior-Aware Confidence Score (Inspired by Papers 10 & 8)
**Motivation**: Papers 10 (Al-Haideri) and 8 (Li et al.) both show that driver behavior classification (defensive vs. aggressive) provides critical context for interpreting SSM values.

**Proposed method**:
- Extend `StochasticPredictor` with a simple **behavior classifier** based on the object's history:
  - If `|Δvx / Δt| > threshold` → object is braking/accelerating aggressively (defensive/evasive)
  - If lateral velocity is increasing over time → lane change in progress
- Condition the PoNM on the detected behavior: $PoNM_{behavioral} = PoNM \times (1 - p_{evasion})$
  - Where $p_{evasion}$ = probability that the object is already executing an evasive maneuver (which means the near-miss may resolve itself)
  
**Expected outcome**: Lower false alarm rate; more realistic confidence scores; novel contribution beyond simple Monte Carlo PoNM.

### 3.2 Adaptive Threshold Selection (Inspired by Papers 1 & 10)
**Motivation**: Paper 1 (Jiao et al.) shows that context-adaptive thresholds are the frontier. Paper 10 (Al-Haideri) provides empirically grounded threshold ranges.

**Proposed method**:
- Add a `ScenarioContext` classification step: highway/urban/intersection/roundabout
- Map context → threshold multipliers: urban intersections use `ttc_near_miss × 1.3` (more lateral activity → higher tolerance), highways use `ttc_near_miss × 0.8` (higher speeds → tighter threshold)
- This is achievable in simulation by varying the synthetic scenario parameters

**Expected outcome**: Demonstrates that the Rule-Based algorithm fails under context shifts (validating the probabilistic approach), while the Stochastic algorithm degrades more gracefully.

### 3.3 Multi-Participant SSM Chains (Inspired by Paper 7)
**Motivation**: Paper 7 (Del Re et al.) shows that 3-vehicle interactions create secondary conflicts not captured by pairwise analysis. Current project only does pairwise analysis.

**Proposed method**:
- After computing pairwise `PredictionResult` for all objects, add a **conflict propagation check**:
  - If Object A receives `REAR_END` near-miss flag AND Object A is itself close to Object B forward...
  - Then flag a **secondary near-miss** for the ego–Object B pair at elevated risk
- Store as `secondary_near_miss=True` in `PredictionResult`

**Expected outcome**: Detects scenario chains that are currently invisible to the algorithm; relevant for `MIXED_NEAR_MISS` scenarios where multiple participants interact.

---

## Recommended Publication Framing

Based on the literature, the strongest thesis framing that differentiates from all 12 reviewed papers is:

> **"Stochastic Ensemble Surrogate Safety Measure Fusion for Robust Near-Miss Prediction in Synthetic Mixed-Traffic Simulation"**

Key differentiators:
1. **vs. Papers 1, 2, 8**: This project is fully simulation-based — no need for real-world data collection; directly controls noise parameters for systematic studies (impossible with naturalistic data)
2. **vs. Papers 4, 5**: This project does not require labeled training data (unlike LSTM/GPR approaches); SSM-based reasoning is fully interpretable
3. **vs. Papers 3, 9**: This project's multi-type scenario generation tests SSMs across all 5 conflict types in one unified experiment (not individual scenario studies)
4. **vs. Papers 10, 12**: This project empirically demonstrates the effect of threshold sensitivity through noise-varying experiments (rather than just behavioral surveys)

**Target journals**: 
- *Accident Analysis & Prevention* (AAP) — matches Papers 2, 8, 9
- *IEEE Transactions on Intelligent Transportation Systems* (TITS) — matches Papers 4, 8
- *Analytic Methods in Accident Research* (AMAR) — matches Paper 1 (the most directly competing work)

**Recommended evaluation table** in the paper (showing what this project's design achieves vs. each competitor):

| Method | Interpretable | No Training Data | Multi-Type | Probabilistic | Noise-Robust |
|---|---|---|---|---|---|
| Rule-Based SSM (This project, baseline) | ✓ | ✓ | ✓ | ✗ | ✗ |
| Stochastic MC-SSM (This project, novel) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Jiao et al. 2024 | ✗ (learning-based) | ✗ | ✓ | ✓ | ✓ |
| PRISMA 2023 | ✗ (regression) | ✗ | ✗ (longitudinal only) | ✓ | ✓ |
| Seq2Seq LSTM 2022 | ✗ | ✗ | ✗ (intersections) | ✗ | ✗ |

This table makes a clear contribution case for the thesis.
