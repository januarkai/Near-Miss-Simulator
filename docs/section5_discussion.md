# V. DISCUSSION

## A. Interpreting the Rule-Based SSM Degeneration

The most striking result in Table IV is the degenerate behaviour of the Rule-Based SSM: despite achieving perfect recall, it contributes zero specificity (TN = 0), making it operationally equivalent to always raising an alarm. This degeneration arises from two compounding properties of the threshold decision system. First, the multi-criteria fusion logic (any one of three SSMs reporting critical values triggers detection) means that even a mild, transient TTC exceedance in a single frame is sufficient to classify an entire object as a near-miss for that frame. Second, the evaluation dataset includes stochastic noise, and sufficiently aggressive noise occasionally pushes safe objects into the TTC warning zone for one or more frames. Because the detection window for each object spans all 150 frames, a single frame-level false alarm is enough to produce an object-level false positive.

This finding is consistent with established limitations of threshold-based SSM systems identified in the literature [3], [7], where fixed-threshold detectors on noisy real-world data consistently elevate FPR to operationally unacceptable levels. The Rule-Based SSM can be improved by requiring the critical condition to persist for several consecutive frames (hysteresis filtering) or by using a multi-frame weighted vote. The MC-SSM intrinsically provides this robustness without additional post-processing: the PoNM score over a 30-particle ensemble acts as an implicit smoothing filter, and the 30% decision threshold rejects transient single-frame exceedances unless a stable portion of the ensemble crosses the critical zone.

## B. Precision-Recall Trade-off Under Probabilistic Scoring

The MC-SSM achieves a substantially higher precision (0.810) at the cost of lower recall (0.567) compared to Rule-Based SSM. This trade-off is a direct consequence of the PoNM $> 0.3$ threshold: objects whose mean TTC is near but not clearly within the critical zone will not consistently exceeds 30% ensemble membership across frames, leading to missed detections (FN = 65).

From an ADAS deployment perspective, the optimal operating point depends on the application context:

- **Alarm systems** where missed alarms are catastrophic (e.g., emergency autonomous braking) require high recall. In this setting, the Rule-Based SSM's recall of 1.000 --- albeit with very high FPR --- or a lower MC-SSM threshold ($PoNM > 0.15$) would be preferred.
- **Driver advisory systems** where false alarms cause alarm fatigue require high precision and low FPR. The MC-SSM's precision (0.810) and FPR (0.133) are significantly more suitable for these applications.
- **Data annotation pipelines** for scene mining benefit from high AUROC regardless of threshold. Both kinematic algorithms (AUROC $\approx$ 0.78--0.80) substantially outperform the Baseline (0.648) for this use case.

The MC-SSM's PoNM threshold is a single tunable parameter that moves the operating point along the precision-recall curve. Future work could learn or adapt this threshold from deployment data using isotonic regression or Platt scaling to achieve calibrated probability estimates across real sensor distributions.

## C. Conflict Type Classification Limitations

The residual classification accuracy for Rule-Based SSM (0.507) and MC-SSM (0.388) is moderate rather than high, primarily because of the unavoidable RIGHT\_OF\_WAY/BROADSIDE confusion discussed in Section IV-D.

After removing the RIGHT\_OF\_WAY → BROADSIDE errors, the per-type accuracy for the remaining four types improves substantially. Rear-end detection is most reliable (both algorithms achieve near-perfect classification once the object is confirmed same-lane and closing). Cut-off detection benefits from the explicit lateral-offset spatial guard ($|d_y| < 2.0\,w_{\text{lane}}$) that prevents far-lateral side-road objects from being misclassified as adjacent-lane intruders. Lane-change detection is noisier due to the aggressive stochastic velocity noise in the simulation, which can push lateral velocities above the 2.5 m/s cap used to separate lane-change from cut-off events.

The instantaneous-state classifier used in both algorithms is a design choice motivated by real-time computational constraints. An alternative approach would model each object's conflict type as a hidden state in a recurrent or sequential classifier that maintains trajectory history. Such approaches have been explored in recent deep learning work [9], [11] but introduce additional latency and model complexity. The geometric rules used here are fully interpretable, produce consistent type labels across sensor modalities, and are computationally trivial (constant-time per object per frame).

## D. Brier Score and Calibration

The MC-SSM's Brier Score advantage (0.258 vs 0.328 for Rule-Based) reflects the fundamental calibration gap between a counting-based probability (PoNM) and a heuristic score. The Rule-Based SSM's confidence score is constructed as an additive sum of binary conditions (tracking duration, multi-SSM agreement, type identification), and its values are concentrated near 0.7--0.9 for near-miss objects, producing systematic overconfidence that inflates the Brier Score.

The Brier Score improvements in Table V are consistent with findings by Gressenbuch et al. [15] who report that ensemble-based methods consistently outperform threshold-based methods on probabilistic accuracy metrics for trajectory prediction. The MC-SSM's 30-particle ensemble provides a tractable approximation of a full posterior over TTC, and increasing the ensemble size (to $N = 100$ or $N = 500$ particles) could further reduce Brier Score at the cost of proportionally higher computation.

## E. Computational Considerations

The MC-SSM runs 30 SSM evaluations per object per frame instead of 1, making it approximately 30× more expensive than the Rule-Based SSM in terms of SSM function calls. For a typical frame at 10 Hz with $K$ tracked objects, the computational cost is $O(30K)$ per frame. For $K = 10$ (as in the evaluation), this is 300 operations per frame at 10 Hz --- well within real-time constraints on any modern embedded processor.

The trade-off between ensemble size $N$ and accuracy-vs-noise robustness is a natural subject for future sensitivity analysis, particularly in scenarios with many simultaneous objects ($K > 20$) where computational budget becomes a practical constraint.

## F. Limitations of the Synthetic Evaluation

The evaluation is conducted entirely on synthetic data generated by the same simulator that parameterises the scenario types. This creates an optimistic evaluation environment where the noise model and scenario distributions are known at training/design time. Real-world evaluation on naturalistic driving datasets (e.g., inD [16], highD [17], or nuScenes [18]) would require re-calibrating the noise covariance $\Sigma_{\text{noise}}$ from observed sensor statistics and validating the conflict type classifier against human-annotated ground truth. The synthetic evaluation serves as a proof of concept that validates the algorithmic design; generalisability to real data remains an open empirical question.

Additionally, the evaluation uses a fixed scenario structure (5 near-miss + 5 safe objects per scenario) that produces an exactly balanced dataset. In deployment, near-miss events are rare (class imbalance ratios of 1:100 to 1:1000 are typical in naturalistic data), which would further amplify the cost of false positives and increase the operational advantage of the MC-SSM's improved precision.
