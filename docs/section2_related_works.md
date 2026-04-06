# II. RELATED WORK

**Paper Title**: *Stochastic Ensemble Surrogate Safety Measure Fusion for Robust Near-Miss Prediction in Synthetic Mixed-Traffic Simulation*

*Written to conform to the IEEE conference two-column template. Lettered subsections follow IEEE conference style (A, B, C…). Citations follow the numeric IEEE style [N]. BibTeX key mappings are listed at the end of `docs/research_paper_structure.md`.*

---

## A. Surrogate Safety Measure Foundations

The quantitative analysis of near-miss events is built on Surrogate Safety Measures — kinematic indicators computed from vehicle trajectories that serve as proxies for collision risk. The Time to Collision (TTC), introduced by Hayward [2], defines the time remaining before impact if both road users maintain their current velocities. Its simplicity and direct physical interpretation made it the dominant SSM in both academic research and commercial ADAS products. The Deceleration Rate to Avoid Collision (DRAC), proposed by Cooper and Ferguson [6], computes the instantaneous braking effort required by a following vehicle to prevent a rear-end collision, complementing TTC for approach scenarios where relative velocity is a more informative signal than distance alone. For intersection conflicts — where road users traverse a shared zone at different times rather than approaching each other head-on — Post-Encroachment Time (PET) [7] measures the temporal gap between the first vehicle leaving the conflict zone and the second arriving; low PET values indicate that the two road users nearly shared the same spatial point simultaneously. Finally, the Minimum Distance Ratio (MDR) normalises the actual inter-vehicle separation against a minimum safe separation threshold, providing a dimensionless spatial closure indicator applicable across vehicle classes of different physical dimensions.

Despite decades of use, a foundational limitation applies across all four measures: each was designed for a specific interaction archetype and calibrated on a specific road and traffic context. TTC is geometrically valid only along the longitudinal axis; DRAC is undefined when relative longitudinal velocity is zero; PET requires full trajectory records and a well-defined conflict zone; MDR is sensitive to the choice of minimum-safe-distance reference. No single SSM universally covers all conflict types encountered in mixed traffic. A comprehensive survey of computer-vision-based trajectory safety analysis by Abdel-Aty et al. [13] confirmed this fragmentation and identified the Bird's Eye View (BEV) trajectory frame as the emerging standard for unified multi-class conflict analysis, noting that BEV eliminates perspective distortion and simplifies SSM calculation compared to roadside or monocular camera perspectives.

## B. Probabilistic and Uncertainty-Aware SSM Extensions

The fundamental inadequacy of deterministic SSMs — their binary cliff-edge threshold behaviour and their reliance on the mean estimated state — has motivated a growing body of work on probabilistic extensions. Jiao et al. [8] proposed a unified probabilistic conflict detection framework that reframes conflict as an extreme tail event of the inter-vehicle proximity distribution. Rather than comparing a single TTC value to a fixed global threshold, their framework learns a context-dependent proximity distribution from naturalistic trajectory data and defines a conflict as occurring when proximity falls into the distribution's extreme tail: $P(\text{conflict}) = P(\text{proximity} < \tau_{\text{context}})$, where $\tau_{\text{context}}$ is inferred from data rather than set by expert judgment. The framework generalises across datasets without retraining and captures the long-tailed distributon of conflict intensity that binary systems miss entirely. However, the approach requires large naturalistic trajectory datasets for context modelling and is not applicable in a simulation-only setting where no field data is available.

PRISMA (Probabilistic RISk Measure derivAtion), proposed by de Gelder et al. [9], derives real-time crash probability through a two-step process: a data-driven trajectory predictor generates a distribution over possible future trajectories rather than a single prediction, and Monte Carlo simulation over this distribution estimates the probability that at least one sample trajectory results in a collision. A regression model caches the Monte Carlo results for real-time inference. PRISMA demonstrates that the distribution of possible TTC values, computed from trajectory uncertainty rather than a point estimate, is wide enough to simultaneously span "safe" and "near-miss" classifications for many real traffic situations — empirically establishing that the mean trajectory is an insufficient basis for binary classification. PRISMA, however, is currently demonstrated only for longitudinal interactions and requires a pre-trained regression model tied to its training traffic context.

Al-Haideri et al. [14] addressed the complementary problem of threshold calibration: rather than fixing $\tau$ by expert judgment, their Latent Class Logit Kernel (LC-LK) model derives behavioural thresholds by modelling latent driver classes (routine vs. defensive) and finding the TTC value at which the probability of a defensive evasive response rises sharply. Applied to naturalistic roundabout data, the model converges on a TTC near-miss threshold of 0.8–1.1 s, consistent with the expert-based value of 1.0 s used in this work and providing behavioural empirical grounding for that configuration.

## C. Trajectory Prediction for Conflict Detection

A parallel research direction replaces kinematic SSMs with learned trajectory predictors, computing TTC from a predicted future trajectory rather than extrapolating the current velocity. Abdelraouf et al. [12] trained a Sequence-to-Sequence LSTM (encoder-decoder architecture) on the CitySim intersection dataset to predict future positions and heading angles up to three seconds ahead. TTC was then computed from the predicted bounding-box overlap rather than center-point proximity — a crucial distinction, as the authors showed that center-point TTC frequently underestimates conflict severity for large vehicles. The model outperformed constant-velocity baselines in conflict identification at urban intersections. However, the Seq2Seq LSTM requires a large labeled training dataset, generalises poorly outside its training context, and produces a binary or deterministic conflict flag rather than a calibrated probability.

Lu et al. [15] extended the trajectory-to-safety-measure pipeline using a Transformer Masked Autoregressive Flow model, training it to learn the joint probability density function of TTC, speed, and acceleration sequences. The model allows counterfactual reasoning — estimating the probability that a crash would have occurred without an observed evasive action — and provides theoretical justification for using Brier Score as the evaluation metric for probabilistic safety predictions. Their empirical finding that TTC sequences alone are insufficient and that acceleration-based features (DRAC-equivalent signals) add critical information supports the multi-SSM fusion design in the present work.

Li et al. [10] specifically addressed pedestrian-vehicle conflict prediction at intersections using Gaussian Process Regression (GPR) to model pedestrian trajectory uncertainty and a Random Forest classifier to detect driver evasive manoeuvres. The GPR provides a Gaussian distribution $\mathcal{N}(\mu(t), \sigma^2(t))$ over pedestrian position at each future time step, enabling a probabilistic conflict probability that accounts for the high velocity variance inherent in pedestrian motion. The framework achieved perfect recall on a LiDAR intersection dataset, demonstrating that constant-velocity assumptions for pedestrians systematically underestimate conflict risk — a finding directly relevant to this work's pedestrian scenario types. The GPR-based approach is conceptually analogous to this paper's Monte Carlo perturbation method: both replace a single trajectory prediction with a distribution. The distinction is that GPR derives its distribution from learned covariance functions fitted to historical trajectories, while the present work uses a fixed Gaussian perturbation model parametrised by sensor noise specifications — trading principled covariance for computational simplicity and zero data requirements.

## D. Two-Dimensional SSM Formulations

The geometric failure of 1D TTC for lateral conflicts has been examined quantitatively by Li et al. [11], who developed a generic analytical SSM framework accommodating 1D, 2D, and 3D vehicle movement models with bounding-box collision criteria. Their analysis found that 1D SSMs introduce errors of up to 300% for non-critical TTC values and approximately 20% even in the critical range below 1.5 s when applied to lateral or turning scenarios. This confirms that bounding-box collision detection — implemented in this work through corner-point geometry — is more accurate than center-point detection, and that conflict-type-aware SSM routing is necessary for reliable multi-type coverage.

Guo et al. [16] proposed a practical 2D-TTC formulation for lane-change scenarios, defined as $TTC_{2D} = \sqrt{TTC_x^2 + TTC_y^2}$, combining longitudinal and lateral TTC components geometrically. Applied to connected-vehicle naturalistic data, 2D-TTC detected significantly more lane-change conflicts than its 1D counterpart, and the detected events correlated strongly with archived crash records, validating it as a reliable SSM for lateral interaction types. Their empirically validated critical threshold of $TTC_{2D} < 1.5$ s for lane-change scenarios provides a grounded reference for the LANE\_CHANGE and CUTOFF conflict type thresholds used in this work.

## E. Multi-Vehicle Interaction and Propagation

Standard SSM analysis evaluates each pair of road users independently. Del Re and Olaverri-Monreal [17] studied three-vehicle lane-change interactions — ego vehicle, lead vehicle, and a lane-changer — and showed that the primary conflict between the lane-changer and the lead vehicle causes the lead vehicle to brake, which then creates a secondary rear-end conflict between the lead vehicle and the ego. Pairwise SSM analysis misses this conflict propagation chain: the ego's safety-critical moment often occurs *after* the primary conflict resolves, when the lane change is complete and the lead vehicle has decelerating. This finding identifies multi-vehicle propagation as an unaddressed gap in pairwise near-miss detection frameworks, including the one presented in this paper, and is acknowledged as future work in Section VI.

Anowar et al. [18] studied heterogeneous non-lane-based traffic conditions, where pedestrians and vehicles routinely cross each other's paths without lane discipline. Their Bayesian Generalised Extreme Value framework, using PET as the primary SSM, demonstrated that PET is the appropriate measure for crossing-type conflicts and that a behaviour-normalised crash risk metric reduces false positives caused by routine gap-acceptance behaviour in high-density pedestrian traffic. The validation of PET for crossing scenarios supports its intended use in the BROADSIDE and RIGHT\_OF\_WAY conflict types in this work, where lateral encroachment rather than longitudinal approach is the primary danger signal.

## F. Positioning This Work

The literature review reveals a consistent pattern: each prior approach improves on one dimension of the near-miss detection problem while leaving others unaddressed. Table I maps the five key properties against the main prior methods and the two algorithms presented in this work.

**Table I. Positioning of This Work Against Prior Methods**

| Method | Interpretable | No Training Data | All 5 Conflict Types | Probabilistic Output | Noise Robustness Studied |
|---|---|---|---|---|---|
| **Stochastic MC-SSM (ours)** | ✓ | ✓ | ✓ | ✓ | ✓ |
| Rule-Based SSM (ours, baseline) | ✓ | ✓ | ✓ | ✗ | ✓ |
| Jiao et al. [8] 2024 | ✗ | ✗ | ✓ | ✓ | ✗ |
| PRISMA [9] 2023 | ✗ | ✗ | ✗ (longitudinal) | ✓ | ✗ |
| Seq2Seq LSTM [12] 2022 | ✗ | ✗ | ✗ (intersections) | ✗ | ✗ |
| 2D-TTC [16] 2022 | ✓ | ✓ | ✗ (lateral only) | ✗ | ✗ |
| Li et al. GPR [10] 2022 | ✗ | ✗ | ✗ (pedestrian) | ✓ | ✗ |

The Stochastic MC-SSM presented in this paper is the only method in the comparison that simultaneously satisfies all five properties. Its key distinguishing characteristic is the combination of full interpretability (every particle's TTC trace is directly auditable) with probabilistic output (PoNM ∈ [0, 1]) achieved without any training data — a combination that no prior method achieves. Additionally, this is the first work to evaluate near-miss detection performance under a controlled, parametric sensor noise sweep, directly addressing the robustness gap identified across all reviewed methods.

---

## Writing Notes (Not for Final Paper)

### Target Length Check
IEEE conference Related Work sections typically run one to one-and-a-half columns (~600–1,000 words). The body above is approximately **950 words** — at the upper end of the target range. Subsection F (positioning table) can be moved to the end of Section III if space is tight; the table itself should be retained as it directly supports the contribution claims.

### Suggested Figures or Tables in This Section
| Item | Placement | Purpose |
|---|---|---|
| Table I (positioning table) | End of Section II-F | Summarises literature gap visually; may alternatively open Section III |

### Citation Number Mapping
| [N] used above | BibTeX key | Reference |
|---|---|---|
| [2] | — | Hayward, J.C., 1972 (TTC) |
| [6] | — | Cooper & Ferguson, 1976 (DRAC) |
| [7] | — | Allen et al., 1978 (PET) |
| [8] | `jiao2024unified` | Jiao et al., 2024, AMAR |
| [9] | `degelder2023prisma` | de Gelder et al., 2023, AAP (PRISMA) |
| [10] | `lipedestrian2022` | Li et al., 2022, TITS (pedestrian GPR) |
| [11] | `li2021ttcbias` | Li et al., 2024, arXiv (1D vs. 2D TTC) |
| [12] | `seq2seq2022` | Abdelraouf et al., 2022, TITS (Seq2Seq LSTM) |
| [13] | `abdelaty2023survey` | Abdel-Aty et al., 2023, AAP (CV survey) |
| [14] | `alhaideri2021` | Al-Haideri et al., 2025, arXiv (LC-LK thresholds) |
| [15] | `gpr2022` | Lu et al., 2022, arXiv (Transformer-MAF) |
| [16] | `ttc2d2023` | Guo et al., 2022, AAP (2D-TTC & DDPG) |
| [17] | `delre2022multi` | Del Re & Olaverri-Monreal, 2023, arXiv (multi-vehicle) |
| [18] | `anowar2021pet` | Anowar et al., 2025, arXiv (Bayesian GEV + PET) |
