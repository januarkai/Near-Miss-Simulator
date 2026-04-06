# III. METHODOLOGY

**Paper Title**: *Stochastic Ensemble Surrogate Safety Measure Fusion for Robust Near-Miss Prediction in Synthetic Mixed-Traffic Simulation*

*Written to conform to the IEEE conference two-column template. Lettered subsections follow IEEE conference style (A, B, C...). Citations follow the numeric IEEE style [N].*

---

The proposed methodology consists of four sequential stages that together form a self-contained, training-data-free near-miss prediction pipeline, as shown in Fig. 1. In Stage A, a parametric ego-centric BEV simulation generates labelled traffic scenarios under controllable stochastic dynamics, producing per-frame state vectors $(d_x, d_y, v_x, v_y)$ and physics-derived ground-truth labels. In Stage B, a priority-ordered conflict-type classifier routes each observation to its geometrically appropriate SSM, ensuring that TTC$_{1D}$, TTC$_{2D}$, DRAC, and MDR are each applied only within their valid kinematic domains. Stage C instantiates the proposed Stochastic Monte Carlo SSM (MC-SSM): a Monte Carlo particle ensemble is constructed around each noisy observation, and the Probability of Near-Miss (PoNM) is derived analytically as the fraction of particles whose TTC falls within the critical zone, yielding a calibrated continuous risk score without any learned parameters. Stage D applies a four-tier evaluation protocol — event-level classification, probabilistic scoring, temporal alignment, and sensor-noise robustness — to quantify algorithmic performance across the full operating envelope.

---

**Fig. 1 — End-to-End Research Pipeline (Stochastic MC-SSM)**

```
  +---------------------------------------------------------------+
  |                    Stage 1: Data Generation                    |
  +---------------------------------------------------------------+
          |                                         |
          | Input:                                  | Input:
          | Simulation config                       | Simulation config
          | (v_ego, Δt, w_lane, T)                 | (v_ego, Δt, w_lane, T)
          v                                         v
  +---------------------+                   +----------------------+
  |  Scenario           |                   |  Stochastic          |
  |  Initialisation     |                   |  Dynamics            |
  |                     |                   |                      |
  |  v_ego = 15.0 m/s   |                   |  ε_t ~ N(0, Σ_sim)   |
  |  Δt    = 0.1 s      |                   |  α_agg = 3.0×        |
  |  w_lane= 3.5 m      |                   |  p_jerk = 0.10/Δt    |
  |  T     = 3.0 s      |                   |  p_sw   = 0.05/Δt    |
  +---------------------+                   +----------------------+
          |                                         |
          | Output:                                 | Output:
          | Road geometry                           | Perturbed states
          | + object layout                         | per time step
          v                                         v
  +---------------------+                   +----------------------+
  |  Object Placement   |                   |  Ground-Truth        |
  |                     |                   |  Labelling           |
  |  n ∈ [3, 7] objects |                   |                      |
  |  Classes:           |                   |  TTC_phys < 1.5 s ?  |
  |   car, truck,       |                   |   YES -> Near-Miss   |
  |   motorcycle,       |                   |         + conflict   |
  |   bicycle,          |                   |         type label   |
  |   pedestrian        |                   |   NO  -> Safe        |
  |  Roles:             |                   +----------------------+
  |   lead, adjacent,   |                           |
  |   crossing, ped,    |                           | Output:
  |   background        |                           | Per-frame label
  |  5 conflict types   |                           | y_t ∈ {0, 1}
  |   (can co-occur)    |                           | + conflict type
  +---------------------+                           |
          |                                         |
          | Output:                                 |
          | Initial object states                   |
          | (dx, dy, vx, vy) per object             |
          +--------------------+--------------------+
                               |
                               | Output: Dataset
                               | X_obs = (dx, dy, vx, vy) per frame
                               | GT label y_t, conflict-type label
                               | Saved to CSV + JSON metadata
                               v
  +---------------------------------------------------------------+
  |                    Stage 2: SSM Routing                        |
  +---------------------------------------------------------------+
                               |
          +--------------------+--------------------+
          |                                         |
          | Input:                                  | Input:
          | X_obs = (dx, dy, vx, vy)               | Conflict-type label
          v                                         v
  +---------------------+                   +----------------------+
  |  Conflict-Type      |                   |  SSM Oracle          |
  |  Classifier         |                   |  (type-routed)       |
  |                     |     type label    |                      |
  |  Priority order:    | ----------------> |  Rear-End:           |
  |  1. Broadside       |                   |   TTC_1D, DRAC       |
  |  2. Right-of-Way    |                   |  Lane-Change:        |
  |  3. Cut-Off         |                   |   TTC_2D             |
  |  4. Lane-Change     |                   |  Cut-Off:            |
  |  5. Rear-End        |                   |   TTC_2D             |
  |                     |                   |  Broadside:          |
  |  Rules on           |                   |   TTC_2D, MDR        |
  |  (dx, dy, vx, vy)   |                   |  Right-of-Way:       |
  |  without map data   |                   |   TTC_2D, MDR        |
  +---------------------+                   +----------------------+
          |                                         |
          | Output:                                 | Output:
          | Conflict-type label                     | SSM value(s)
          | {Rear-End, Lane-Change,                 | TTC / DRAC / MDR
          |  Cut-Off, Broadside,                    | per object
          |  Right-of-Way}                          | per frame
          +--------------------+--------------------+
                               |
                               | Output:
                               | (conflict-type, routed SSM value)
                               | per object per frame
                               v
  +---------------------------------------------------------------+
  |                    Stage 3: Stochastic MC-SSM  [PROPOSED]      |
  +---------------------------------------------------------------+
                               |
                               | Input:
                               | X_obs = (dx, dy, vx, vy)
                               | routed SSM oracle
                               v
                    +---------------------+
                    |  Particle           |
                    |  Generation         |
                    |                     |
                    |  N = 30 samples     |
                    |  X^(i) ~ N(X_obs,   |
                    |  diag(σ_p²,σ_v²))  |
                    |  σ_p = 0.5 m        |
                    |  σ_v = 1.0 m/s      |
                    +---------------------+
                               |
                               | Output: 30 perturbed
                               | state vectors X^(i)
                               |
             +-----------------+-----------------+
             |                 |                 |
             | X^(1)           | X^(2) ... X^(N) |
             v                 v                 v
    +---------------+                   +---------------+
    | Per-Particle  |        ...        | Per-Particle  |
    | Conflict-Type |                   | Conflict-Type |
    | Classifier    |                   | Classifier    |
    +---------------+                   +---------------+
             |                                   |
             | type_i                            | type_N
             v                                   v
    +---------------+                   +---------------+
    | Per-Particle  |        ...        | Per-Particle  |
    | SSM Oracle    |                   | SSM Oracle    |
    | -> TTC^(i)    |                   | -> TTC^(N)    |
    +---------------+                   +---------------+
             |                                   |
             | Output: TTC^(i)                   | Output: TTC^(N)
             +-----------------+-----------------+
                               |
                               | Output: 30 TTC values
                               v
                    +---------------------+
                    |  PoNM Aggregation   |
                    |                     |
                    |  PoNM = (1/N) Σᵢ   |
                    |    1(TTC^(i) < τ)   |
                    |  τ = 1.0 s          |
                    |  PoNM ∈ [0.0, 1.0]  |
                    +---------------------+
                               |
                               | Output: PoNM score
                               |
                    +----------+----------+
                    |  Decision Gate      |
                    |  PoNM > δ, δ=0.3 ?  |
                    +----------+----------+
                    /                      \
        YES: PoNM > δ             NO: PoNM ≤ δ
                  |                        |
                  v                        v
       +-------------------+    +-------------------+
       |  Near-Miss        |    |  Safe             |
       |  flag = 1         |    |  flag = 0         |
       |  conf = PoNM      |    |  conf = PoNM      |
       +-------------------+    +-------------------+
                  |                        |
                  +----------+------------+
                             |
                             | Output:
                             | (near-miss flag, PoNM,
                             |  conflict-type label)
                             | per object per frame
                             v
  +---------------------------------------------------------------+
  |                    Stage 4: Evaluation Protocol                |
  +---------------------------------------------------------------+
                               |
          +--------------------+--------------------+
          |             |              |            |
          | Input:      | Input:       | Input:     | Input:
          | flag, y_t   | PoNM, y_t   | flag, y_t  | PoNM, y_t
          v             v              v            v
  +----------+   +-----------+   +----------+   +----------+
  | D1.      |   | D2.       |   | D3.      |   | D4.      |
  | Event-   |   | Probab-   |   | Temporal |   | Robust-  |
  | Level    |   | ilistic   |   | Quality  |   | ness     |
  | Metrics  |   | Quality   |   | Metrics  |   | Study    |
  +----------+   +-----------+   +----------+   +----------+
        |               |               |               |
        | Output:       | Output:       | Output:       | Output:
        | Precision     | Brier Score   | t-IoU         | RC coeff
        | Recall        | AUROC         | TTA (s)       | per σ_p
        | F1, FPR, FNR  |               | type accuracy | level
```

*Fig. 1. End-to-end pipeline of the proposed Stochastic MC-SSM framework. Each box shows a processing step with explicit inputs and outputs on connecting arrows. Stages 1–4 correspond to Sections III-A through III-D.*

---

## A. Stage A — Simulation Framework and Data Generation

Fig. 2 illustrates the data generation pipeline. All experiments are conducted inside a purpose-built ego-centric Bird's Eye View (BEV) simulation environment.

```
  Input: Simulation configuration
  (v_ego = 15.0 m/s, Δt = 0.1 s, w_lane = 3.5 m, T = 3.0 s)
                               |
                               v
              +-----------------------------------------+
              |  Scenario Initialisation                 |
              |                                         |
              |  ego at origin (0, 0)                   |
              |  v_ego = 15.0 m/s (fixed)               |
              |  3-lane road geometry                   |
              |  w_lane = 3.5 m  |  Δt = 0.1 s         |
              +-----------------------------------------+
                               |
                               | Output: Road geometry + ego state
                               v
              +-----------------------------------------+
              |  Object Placement                        |
              |                                         |
              |  n ∈ [3, 7] surrounding objects         |
              |  Classes: car, truck, motorcycle,       |
              |           bicycle, pedestrian           |
              |  Roles: lead, adjacent, crossing,       |
              |         pedestrian, background          |
              |  Conflict types (co-occur):             |
              |    rear-end, lane-change, cut-off,      |
              |    broadside, right-of-way              |
              +-----------------------------------------+
                               |
                               | Output: Initial object states
                               | (dx, dy, vx, vy) per object
                               v
              +-----------------------------------------+
              |  Stochastic Dynamics  (per time step)    |
              |                                         |
              |  Input: X_t = (dx, dy, vx, vy)          |
              |  ε_t ~ N(0, diag(σ_p², σ_p²,           |
              |                   σ_v², σ_v²))          |
              |  α_agg = 3.0×                           |
              |  p_jerk  = 0.10 per Δt                  |
              |  p_sw    = 0.05 per Δt                  |
              |  Robustness sweep:                      |
              |  σ_p ∈ {0.5, 1.0, 2.0, 4.0, 8.0} m    |
              |  σ_v = 2σ_p  m/s                        |
              +-----------------------------------------+
                               |
                               | Output: Perturbed state
                               | (dx, dy, vx, vy) per object per step
                               v
              +-----------------------------------------+
              |  Ground-Truth Labelling  (per frame)     |
              |                                         |
              |  Input: X_t = (dx, dy, vx, vy)          |
              |  Compute TTC_phys (physics-derived)     |
              |                                         |
              |  TTC_phys < 1.5 s ?                     |
              |             /          \               |
              |           YES           NO             |
              |            |             |             |
              |     y_t = 1          y_t = 0           |
              |   (Near-Miss)         (Safe)           |
              |  + record conflict type label          |
              +-----------------------------------------+
                               |
                               | Output: Labelled frame dataset
                               v
              +-----------------------------------------+
              |  Dataset Output                          |
              |                                         |
              |  Per-frame state: (dx, dy, vx, vy)      |
              |  GT label: y_t ∈ {0=safe, 1=near-miss}  |
              |  Conflict type label per frame          |
              |  Format: CSV rows + JSON metadata       |
              +-----------------------------------------+
                               |
                               | Output: Labelled dataset files
                               | (CSV + JSON) -> Stage B input
```

In the BEV coordinate frame the ego vehicle is fixed at the origin at all times, with the positive $x$-axis aligned to its heading and the positive $y$-axis pointing left. All surrounding objects are expressed in this continuously recentred frame, so every SSM reduces to scalar operations on the relative state $\mathbf{X}_t = (d_x, d_y, v_x, v_y)^\top$ without inter-frame coordinate transforms. The ego travels at $v_{\text{ego}} = 15.0$ m/s within a three-lane geometry ($w_{\text{lane}} = 3.5$ m, $dt = 0.1$ s, total horizon $T = 3.0$ s).

Each scenario embeds $n \in [3, 7]$ surrounding road users drawn from five object classes with physically representative dimensions, which govern placement geometry and physics-based TTC computation but are intentionally withheld from the algorithm under evaluation. Each object is assigned a behavioural role $r \in \{\text{lead, adjacent, crossing, pedestrian, background}\}$ that determines its initial spatial zone and nominal speed range. All five canonical conflict types — rear-end, lane-change, cut-off, broadside, right-of-way — can co-occur within a single scenario, yielding a unified multi-type test bed.

Per-step stochastic dynamics perturb both position and velocity with additive zero-mean Gaussian noise: $\boldsymbol{\epsilon}_t \sim \mathcal{N}(\mathbf{0}, \Sigma_{\text{sim}})$ where $\Sigma_{\text{sim}} = \text{diag}(\sigma_p^2, \sigma_p^2, \sigma_v^2, \sigma_v^2)$. An aggression multiplier of $3.0\times$ scales the baseline noise amplitude. The stochastic dynamics additionally include a 10\% per-step probability of a sudden velocity impulse and a 5\% per-step probability of a lateral swerve, modelling irregular urban driver behaviour beyond constant-velocity assumptions [12].

Ground truth is assigned per frame: a near-miss label $y_t = 1$ is emitted whenever the physics-derived $\text{TTC}_{\text{physics}} < 1.5$ s between the designated risk actor and the ego; otherwise $y_t = 0$. The conflict type is recorded alongside the label. For the Stage D robustness study, $\sigma_p$ is swept over $\{0.5, 1.0, 2.0, 4.0, 8.0\}$ m with $\sigma_v = 2\sigma_p$ m/s; all other parameters remain fixed, enabling attribution of metric variation to sensor uncertainty alone.

## B. Stage B — SSM Calculator and Conflict-Type Routing

Let $\mathbf{X}_{\text{obs}} = (d_x, d_y, v_x, v_y)^\top$ denote the ego-relative state of a surrounding object at time step $t$, where $(d_x, d_y)$ is the centroid-to-centroid separation and $(v_x, v_y)$ is the relative velocity in the ego-centric frame. Four SSMs are defined over this state vector, each valid within a distinct conflict geometry. A priority-ordered geometric classifier maps each observation to exactly one conflict type, and the corresponding SSM oracle is invoked. All quantities are computed on centroid separations; bounding-box dimensions are excluded because sensor-estimated sizes carry insufficient reliability for safety-critical kinematic computations.

**Longitudinal TTC (TTC$_{1D}$)** is computed whenever the object is located ahead of the ego ($d_x > 0$) and closing ($v_{\text{rel},x} > 0$):

$$TTC_{1D} = \frac{d_x}{\,v_{\text{rel},x}\,}$$

where $d_x$ is the longitudinal centroid-to-centroid separation. All distances are measured between object centroids and the ego origin; bounding-box dimensions are excluded because sensor-estimated sizes carry insufficient reliability for safety-critical computations. As quantified by Li et al. [11], applying one-dimensional TTC to lateral interaction types introduces errors of up to 300%.

**Two-dimensional TTC (TTC$_{2D}$)** projects both the ego and object centroids forward in time under a constant-velocity assumption and identifies the first time step at which the predicted centroid separation falls within a fixed conflict-zone threshold. This measure is applied to lateral conflict types --- lane-change and cut-off --- where the longitudinal TTC is geometrically invalid and the relative risk is carried primarily in the lateral dimension [16].

**DRAC** quantifies the instantaneous deceleration demand for rear-approach scenarios:

$$DRAC = \frac{v_{\text{rel},x}^2}{2\, d_x}$$

Higher DRAC values indicate greater urgency; the measure is only defined when $d_x > 0$ and $v_{\text{rel},x} > 0$, bounding its application to forward-closing longitudinal interactions.

**MDR** provides a dimensionless spatial closure indicator applicable across all object classes regardless of speed:

$$MDR = \frac{d_{\text{current}}}{d_{\text{initial}}}$$

where $d_{\text{initial}}$ is the separation at scenario onset. Values below 0.5 signal that the gap has closed to less than half its initial value, indicating rapid spatiotemporal convergence.

Table II summarises the three-tier risk thresholds. Prior to SSM computation, the conflict type is determined by five geometric rules evaluated in priority order against $\mathbf{X}_{\text{obs}}$ (Table III). Lane membership is resolved from $d_y$ alone without map data. In the ego-centric frame, cross-traffic objects exhibit $v_x \approx -v_{\text{ego}}$ regardless of their own speed, making $v_x$ an unreliable discriminator; the primary lateral discriminator is therefore $\lvert d_y \rvert$: objects from $\lvert d_y \rvert \geq 1.5\,w_{\text{lane}}$ are classified as BROADSIDE or RIGHT-OF-WAY, while adjacent-lane objects ($\lvert d_y \rvert \approx w_{\text{lane}}$) are classified as CUT-OFF or LANE-CHANGE. Residual confusion between BROADSIDE and RIGHT-OF-WAY during active crossing is an acknowledged limitation of purely instantaneous-state classifiers.

**Table II. SSM Risk-Level Thresholds**

| SSM | Safe | Warning | Near-Miss |
|---|---|---|---|
| TTC (s) | > 4.0 | 1.0 - 4.0 | < 1.0 |
| DRAC (m/s2) | < 3.0 | 3.0 - 6.0 | > 6.0 |
| MDR | > 0.8 | 0.5 - 0.8 | < 0.5 |

**Table III. Conflict Type Detection Rules**

Lane zone definitions (ego-centric lateral offset $d_y$, with $w_{\text{lane}} = 3.5$ m):
- **Same lane**: $\lvert d_y \rvert < w_{\text{lane}}/2 = 1.75$ m
- **Adjacent lane**: $w_{\text{lane}}/2 \leq \lvert d_y \rvert < 1.5\,w_{\text{lane}} = 5.25$ m
- **Far lateral (side road)**: $\lvert d_y \rvert \geq 1.5\,w_{\text{lane}} = 5.25$ m

Because the ego vehicle is fixed at the coordinate origin, $d_y = 0$ is always the ego centreline. Lane membership requires no map data; it is resolved from the instantaneous lateral offset alone. Rules are evaluated in priority order (Broadside first); the first matching rule is returned.

| Type | Detection Condition |
|---|---|
| Broadside | $-10\ \text{m} < d_x < 45\ \text{m}$ (intersection zone) **and** $\lvert v_y \rvert > 4.0$ m/s (fast lateral crossing) **and** not same lane |
| Right-of-Way | $0 < d_x < 60$ m **and** $\lvert d_y \rvert > 1.5\,w_{\text{lane}}$ (side-road lateral offset) **and** $\lvert v_y \rvert > 0.3$ m/s toward ego centreline |
| Cut-Off | $0 < d_x < 40$ m **and** $0 < \lvert d_y \rvert < 2.0\,w_{\text{lane}} = 7.0$ m (not same lane) **and** lateral velocity toward ego centreline with $\lvert v_y \rvert > 0.5$ m/s |
| Lane-Change | Adjacent lane **and** $\lvert v_y \rvert < 2.5$ m/s (gradual drift) **and** lateral velocity toward ego centreline **and** $v_{\text{rel},x} > 3.0$ m/s |
| Rear-End | $d_x > 0$ (object ahead) **and** $\lvert d_y \rvert < w_{\text{lane}}/2$ (same lane) **and** $\lvert v_y \rvert < 1.0$ m/s **and** $v_{\text{rel},x} > 1.0$ m/s |

## C. Stage C — Stochastic MC-SSM (Proposed Method)

Conventional SSM evaluation treats $\mathbf{X}_{\text{obs}}$ as a deterministic point estimate, which collapses the continuous uncertainty distribution of a real sensor into a single scalar decision. The proposed Stochastic MC-SSM replaces this point evaluation with a Monte Carlo particle ensemble that explicitly marginalises over sensor noise, yielding a calibrated probability estimate rather than a hard threshold crossing. The per-frame prediction pipeline is shown in Fig. 3.

```
  Input: X_obs = (dx, dy, vx, vy)  [observed state at frame t]
  Input: σ_p = 0.5 m, σ_v = 1.0 m/s
                               |
                               v
              +------------------------------------------+
              |  Particle Generation                      |
              |                                          |
              |  X^(i) ~ N(X_obs, diag(σ_p²,σ_p²,       |
              |                        σ_v²,σ_v²))       |
              |  i = 1, 2, ..., N=30                     |
              +------------------------------------------+
                               |
                               | Output: 30 perturbed state vectors
                               | X^(1), X^(2), ..., X^(30)
                               |
         +-----------+---------+---------+-----------+
         |           |         |         |           |
         | X^(1)     | X^(2)   |   ...   | X^(N)     |
         v           v                   v           v
  +------------+ +------------+    +------------+ +------------+
  | Conflict-  | | Conflict-  |    | Conflict-  | | Conflict-  |
  | Type       | | Type       |    | Type       | | Type       |
  | Classifier | | Classifier |    | Classifier | | Classifier |
  | (5 rules)  | | (5 rules)  |    | (5 rules)  | | (5 rules)  |
  +------------+ +------------+    +------------+ +------------+
         |           |                   |           |
         | type^(1)  | type^(2)          | type^(N-1)| type^(N)
         v           v                   v           v
  +------------+ +------------+    +------------+ +------------+
  | SSM Oracle | | SSM Oracle |    | SSM Oracle | | SSM Oracle |
  | TTC_1D or  | | TTC_1D or  |    | TTC_1D or  | | TTC_1D or  |
  | TTC_2D     | | TTC_2D     |    | TTC_2D     | | TTC_2D     |
  +------------+ +------------+    +------------+ +------------+
         |           |                   |           |
         | TTC^(1)   | TTC^(2)           | TTC^(N-1) | TTC^(N)
         +-----------+---------+---------+-----------+
                               |
                               | Output: {TTC^(i)}  i=1..30
                               v
              +------------------------------------------+
              |  PoNM Aggregation                         |
              |                                          |
              |  Input: {TTC^(i)}, threshold τ = 1.0 s   |
              |  PoNM = (1/N) Σᵢ 1(TTC^(i) < τ)         |
              |  PoNM ∈ [0.0, 1.0]                       |
              +------------------------------------------+
                               |
                               | Output: PoNM score in [0, 1]
                               v
              +------------------------------------------+
              |  Decision Gate                            |
              |                                          |
              |  Input: PoNM, threshold δ = 0.3          |
              |  Is PoNM > δ ?                           |
              +------------------------------------------+
                         /              \
         YES: PoNM > δ                   NO: PoNM ≤ δ
                       |                       |
                       v                       v
             +-------------------+   +-------------------+
             |  Near-Miss        |   |  Safe             |
             |                   |   |                   |
             |  flag  = 1        |   |  flag  = 0        |
             |  conf  = PoNM     |   |  conf  = PoNM     |
             +-------------------+   +-------------------+
                       |                       |
                       +-----------+-----------+
                                   |
                                   | Output:
                                   | (flag, PoNM, conflict-type label)
                                   | per object per frame
                                   | -> Stage D input
```

At each time step $t$, $N = 30$ particle samples are drawn from the sensor noise model:

$$\mathbf{X}^{(i)} \sim \mathcal{N}\!\left(\mathbf{X}_{\text{obs}},\; \Sigma_{\text{noise}}\right), \quad \Sigma_{\text{noise}} = \text{diag}\!\left(\sigma_p^2,\, \sigma_p^2,\, \sigma_v^2,\, \sigma_v^2\right), \quad i = 1, \ldots, N$$

with $\sigma_p = 0.5$ m and $\sigma_v = 1.0$ m/s representing a conservative ADAS sensor uncertainty budget. Each particle $\mathbf{X}^{(i)}$ is passed independently through the Stage B conflict-type classifier and the corresponding SSM oracle to yield $\text{TTC}^{(i)}$. The Probability of Near-Miss is then the empirical fraction of particles that fall within the critical TTC zone:

$$\text{PoNM} = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}\!\left(\text{TTC}^{(i)} < \tau\right), \quad \tau = 1.0\ \text{s}$$

PoNM $\in [0, 1]$ constitutes the continuous output of the algorithm and serves directly as the confidence score for probabilistic evaluation. A binary near-miss flag is obtained by thresholding: $\hat{y}_t = \mathbb{1}(\text{PoNM} > \delta)$ with $\delta = 0.3$. This ensemble formulation resolves the hard-boundary discontinuity of purely deterministic SSM evaluation: two observations at $\text{TTC} = 1.51$ s and $\text{TTC} = 1.49$ s — bracketing a threshold — produce continuously varying PoNM values that reflect their shared proximity to the critical zone, rather than being assigned to opposite sides of a binary decision. The $N = 30$ ensemble is computationally tractable at standard sensor rates of 10–20 Hz without GPU acceleration.

## D. Stage D — Evaluation Protocol

A four-tier evaluation framework is applied to the proposed algorithm, with binary comparison baselines (distance threshold and deterministic SSM fusion) providing reference bounds. The protocol is designed to assess performance across the binary, probabilistic, temporal, and robustness dimensions simultaneously.

**Event-level classification (D1).** Given a set of $M$ frames, the algorithm output $\hat{y}_t \in \{0,1\}$ is compared to the ground-truth label $y_t \in \{0,1\}$ to populate a confusion matrix $\{\text{TP}, \text{TN}, \text{FP}, \text{FN}\}$. A scenario-level True Positive is scored if $\hat{y}_t = 1$ at any step within a ground-truth event window. Precision $= \text{TP}/(\text{TP}+\text{FP})$, Recall $= \text{TP}/(\text{TP}+\text{FN})$, and $F_1 = 2 \cdot \text{Prec} \cdot \text{Rec}/(\text{Prec}+\text{Rec})$ are reported alongside FPR and FNR.

**Probabilistic quality (D2).** The Brier Score is used as the primary scalar loss for the continuous PoNM output:

$$BS = \frac{1}{M}\sum_{j=1}^{M}\!\left(\hat{p}_j - y_j\right)^2$$

where $\hat{p}_j = \text{PoNM}_j \in [0,1]$. Lower BS indicates better probabilistic calibration. The Area Under the ROC Curve (AUROC) is derived from the full PoNM score distribution and quantifies discrimination across all possible decision thresholds $\delta$.

**Temporal quality (D3).** Temporal Intersection-over-Union measures event boundary accuracy:

$$t\text{-}IoU = \frac{|T_{\text{GT}} \cap T_{\text{pred}}|}{|T_{\text{GT}} \cup T_{\text{pred}}|}$$

where $T_{\text{GT}}$ and $T_{\text{pred}}$ are the time intervals of ground-truth and predicted events respectively. Time-to-Alarm (TTA) records the lead time $\Delta t = t_{\text{alarm}} - t_{\text{onset}}$, where positive values denote early warning. Conflict-type accuracy is evaluated as a multi-class metric restricted to events with $t\text{-}IoU > 0.5$.

**Robustness study (D4).** The complete pipeline is re-executed at each of five noise levels: $\sigma_p \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$ m with $\sigma_v = 2\sigma_p$ m/s. The Robustness Consistency coefficient is the slope of the performance degradation curve:

$$RC = \frac{dM}{d\sigma_p}$$

where $M$ is the chosen performance metric (Brier Score for the proposed MC-SSM). A smaller $|RC|$ indicates more graceful degradation under increasing sensor uncertainty.

---

## Writing Notes (Not for Final Paper)

### Target Length Check
IEEE conference methodology sections typically run two to three columns (~1,000-1,500 words). The body above is approximately **1,100 words** --- within target range. Tables II and III count toward the column width budget.

### Suggested Figures in This Section
| Figure | Placement | Purpose |
|---|---|---|
| Fig. 1: Pipeline block diagram (Data Generation -> SSM Routing -> 3 Algorithms -> Evaluation) | Opening of Section III | Gives reader the system overview at a glance |
| Fig. 3: BEV coordinate frame diagram (ego at origin, 5 object roles labelled) | Section III-A | Illustrates the coordinate system and spatial placement logic |
| Fig. 4: Particle sampling schematic for Algorithm C | Section III-C | Visualises the N=30 ensemble around the observed state |

### Parameter Summary Table (for Appendix or Table IV)
| Parameter | Symbol | Value |
|---|---|---|
| Simulation timestep | dt | 0.1 s |
| Prediction horizon | --- | 3.0 s |
| Ego longitudinal velocity | v_ego | 15.0 m/s |
| Lane width | w_lane | 3.5 m |
| TTC near-miss threshold | tau_near-miss | 1.0 s |
| DRAC near-miss threshold | --- | 6.0 m/s2 |
| MDR near-miss threshold | --- | 0.5 |
| Monte Carlo sample count | N | 30 |
| Position uncertainty (default) | sigma_p | 0.5 m |
| Velocity uncertainty (default) | sigma_v | 1.0 m/s |
| PoNM binary decision threshold | --- | 0.3 |
| Distance baseline threshold | --- | 8.0 m |
| Temporal history window | --- | 30 time steps |
| Aggression noise multiplier | --- | 3.0x |
| Per-step jerk probability | --- | 10% |
| Per-step lateral swerve probability | --- | 5% |
