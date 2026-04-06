# I. INTRODUCTION

**Paper Title**: *Stochastic Ensemble Surrogate Safety Measure Fusion for Robust Near-Miss Prediction in Synthetic Mixed-Traffic Simulation*

*Written to conform to the IEEE conference two-column template. Citations follow the numeric IEEE style [N]. BibTeX key mappings are listed at the end of `docs/research_paper_structure.md`.*

---

Road traffic crashes claim approximately 1.19 million lives annually [1], yet their rarity makes proactive risk analysis statistically difficult — near-miss events, defined as interactions that would have resulted in collision without evasive action [2], occur at roughly 500 times the crash frequency [3], [4] while preserving the same causal mechanisms, making them the preferred risk proxy in both research and ADAS applications where decisions must be made in under 200 milliseconds [5]. The standard computational tool is the Surrogate Safety Measure (SSM) — a kinematic trajectory-derived risk indicator — with TTC, DRAC [6], PET [7], and MDR being the most established; however, deterministic SSM systems exhibit four structural limitations: fixed thresholds create a cliff-edge boundary that misrepresents continuous conflict severity [8]; sensor positional (0.2–1.0 m) and velocity (0.5–2.0 m/s) uncertainty is discarded rather than propagated [9]; tail-risk events invisible to mean-trajectory evaluation go undetected [10]; and the 1D TTC formulation introduces errors of up to 300% when applied to lateral conflict types [11].

Several recent works have addressed individual aspects of these limitations. Abdelraouf et al. [12] used a Seq2Seq LSTM to predict bounding-box-level TTC at intersections, demonstrating that trajectory-based prediction improves over instantaneous-state estimation. Lu et al. [13] proposed a causal Transformer-based framework that derives conditional crash probability from SSM time series, showing that TTC alone is insufficient and multi-feature fusion is necessary for accurate probabilistic output. Abdel-Aty et al. [14] surveyed the full CV-to-SSM pipeline and identified cumulative detection and tracking errors — particularly from inaccurate vehicle geometry estimation — as the dominant degradation source, establishing BEV-based approaches as the most reliable geometric foundation. Del Re and Olaverri-Monreal [15] demonstrated that pairwise SSM analysis misses conflict-propagation effects in multi-vehicle interactions: a lane-changing vehicle forces the lead to brake, creating a secondary rear-end risk for the ego that per-pair computation cannot detect. However, all of these approaches share at least one unresolved shortcoming: they require large naturalistic datasets or trained models; they address only a single conflict geometry rather than the full multi-type spectrum; or they sacrifice interpretability through black-box inference, complicating regulatory certification under ISO 21448 (SOTIF). Critically, no prior work evaluates SSM robustness under controlled, parametrically varied sensor noise — leaving the fundamental question "at what noise level does a given algorithm fail?" unanswered.

This paper addresses these gaps with a simulation-based comparative study. We propose and evaluate the **Stochastic Monte Carlo SSM Fusion (Stochastic MC-SSM)** — an interpretable, training-data-free probabilistic extension of the SSM pipeline. For each observed object state $\mathbf{X}_\text{obs}$ at time $t$, the method generates $N = 30$ Gaussian-perturbed particle samples, evaluates TTC through the full multi-type SSM pipeline for each particle, and aggregates the results into a continuous Probability of Near-Miss score:

$$PoNM = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}\!\left(TTC^{(i)} < \tau_{\text{near\_miss}}\right)$$

Unlike prior probabilistic methods, the Stochastic MC-SSM requires no training data, produces an auditable per-particle decision trace, and is evaluated inside a purpose-built BEV synthetic simulator in which sensor noise level $\sigma$ is a first-class experimental parameter — enabling the controlled robustness study that the literature lacks.

The specific contributions of this paper are:

- **C1.** A Python-based ego-centric Bird's Eye View (BEV) synthetic traffic simulator that generates mixed-traffic near-miss scenarios covering all five canonical conflict types (rear-end, lane-change, cut-off, broadside, right-of-way) under parametrically controlled stochastic noise.
- **C2.** A multi-type rule-based SSM baseline that routes each conflict type to its appropriate SSM (TTC for rear-end, DRAC for following, MDR for spatial closure), establishing the performance ceiling of deterministic near-miss detection.
- **C3.** The proposed Stochastic MC-SSM algorithm, which produces a continuous PoNM score without any trained model or historical data, constituting the primary novel contribution.
- **C4.** A unified evaluation protocol — Brier Score, AUROC, Temporal IoU (t-IoU), and Time-to-Accident (TTA) — applicable equally to binary-output (deterministic) and continuous-output (probabilistic) algorithms; t-IoU and TTA are novel to the near-miss SSM literature.
- **C5.** A controlled $\sigma$-sweep robustness experiment ($\sigma_p \in \{0.5, 1.0, 2.0, 4.0, 8.0\}$ m) that empirically characterises the noise level at which deterministic SSM performance collapses and demonstrates the graceful degradation of the Stochastic MC-SSM.

The remainder of this paper is organized as follows. Section II reviews related work on SSM foundations, probabilistic extensions, trajectory-prediction-based conflict detection, and multi-vehicle analysis. Section III describes the simulation framework, the three algorithm implementations, and the evaluation protocol. Section IV presents experimental results, including the robustness curves, temporal quality metrics, per-conflict-type accuracy, and PoNM calibration analysis. Section V discusses the results in relation to prior work using a structured metric comparison. Section VI concludes the paper and outlines future work directions.

---

## Writing Notes (Not for Final Paper)

### Target Length Check
IEEE conference introductions typically occupy one column to one full page (~500–800 words). The body above is approximately **750 words** — within the IEEE conference target range. If the paper is over the page limit, trim the third paragraph (prior work critique) from four sentences to two.

### Suggested Figures in This Section
| Figure | Placement | Purpose |
|---|---|---|
| Fig. 1: BEV snapshot of a MIXED\_NEAR\_MISS scenario | After second paragraph or alongside C1 | Immediate visual context for the simulator |
| Fig. 2: PoNM vs. TTC curve showing smooth transition vs. hard threshold step function | Alongside the PoNM equation | Makes the binary rigidity argument concrete |

### Citation Number Mapping (replace [N] with actual bibliography numbers in the final paper)
| [N] used above | BibTeX key | Reference |
|---|---|---|
| [1] | — | WHO Global Status Report on Road Safety, 2023 |
| [2] | — | Hayward, J.C., 1972 (TTC definition) |
| [3] | — | Hydén, C., 1987 (conflict frequency ratio) |
| [4] | — | AASHTO, 2010 |
| [5] | — | NHTSA FCW performance guidelines, 2022 |
| [6] | — | Cooper & Ferguson, 1976 (DRAC) |
| [7] | — | Allen et al., 1978 (PET) |
| [8] | `jiao2024unified` | Jiao et al., 2024, AMAR |
| [9] | `degelder2023prisma` | de Gelder et al., 2023, AAP (PRISMA) |
| [10] | `lipedestrian2022` | Li et al., 2022, TITS (pedestrian GPR) |
| [11] | `li2021ttcbias` | Li et al., 2024, arXiv (1D vs. 2D TTC) |
| [12] | `seq2seq2022` | Abdelraouf et al., 2022, TITS (Seq2Seq LSTM) |
| [13] | `lu2022causal` | Lu et al., 2022, arXiv (causal SSM-to-crash-probability) |
| [14] | `abdelaty2023survey` | Abdel-Aty et al., 2023, AAP (CV-to-SSM pipeline survey) |
| [15] | `delre2023multivehicle` | Del Re & Olaverri-Monreal, 2023, arXiv (multi-vehicle SSM) |
