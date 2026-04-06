# VI. CONCLUSION

This paper presented a Stochastic Monte Carlo Safety Surrogate Measure approach (MC-SSM) for vehicle near-miss prediction in ego-centric Bird's-Eye View scenarios. Drawing on established SSM theory and probabilistic ensemble methods, the MC-SSM extends the deterministic Rule-Based SSM framework by replacing single-point state evaluation with a 30-particle ensemble drawn from a Gaussian noise model of ADAS sensor uncertainty. The probability of near-miss (PoNM) confidence score derived from this ensemble provides a continuous, well-calibrated output that resolves the binary rigidity problem inherent in threshold-based detection systems.

The proposed method was evaluated against a naive Distance Baseline (Algorithm A) and a Rule-Based SSM (Algorithm B) on a synthetic dataset of 30 mixed near-miss scenarios across five conflict types. The key empirical findings are as follows:

1. **Specificity**: The MC-SSM (Algorithm C) achieves a false-positive rate of 0.133, compared to 0.413 for the Baseline and 1.000 for the Rule-Based SSM. The Rule-Based SSM flags every scenario as near-miss, producing zero true negatives, which renders it operationally unusable for any application where false alarms have a cost.

2. **Overall accuracy**: MC-SSM achieves the highest classification accuracy (0.717) and precision (0.810), demonstrating that probabilistic ensembling yields a net improvement in detection quality despite the slightly lower recall (0.567 vs 1.000).

3. **Probability calibration**: MC-SSM's Brier Score (0.258) is lower than that of Rule-Based SSM (0.328) and the Baseline (0.360), confirming that the PoNM score is better calibrated as an estimate of near-miss probability.

4. **Discriminative capacity**: AUROC values of 0.802 (Rule-Based TSM) and 0.775 (MC-SSM) both substantially exceed the Baseline (0.648), with Rule-Based SSM's higher AUROC reflecting strong ranking sensitivity while its binary threshold prevents operational use.

5. **Conflict type classification**: Both kinematic algorithms achieve moderate type accuracy (0.507 and 0.388 respectively), with the dominant confusion pattern being RIGHT\_OF\_WAY misclassified as BROADSIDE --- a fundamental kinematic ambiguity that cannot be resolved by instantaneous-state classifiers without multi-frame trajectory history.

The results validate the core hypothesis: replacing a single deterministic TTC evaluation with a stochastic ensemble improves precision and probability calibration at the cost of recall, producing a more operationally appropriate detector for driver advisory and data annotation applications. The ensemble noise covariance $\Sigma_{\text{noise}}$ provides a principled representation of sensor uncertainty that connects directly to ADAS sensor specifications.

**Future Work.** Several extensions are identified for future investigation:

- *Adaptive ensemble sizing*: Dynamically adjusting $N$ based on the number of tracked objects and available computational budget to maintain real-time performance in dense traffic.
- *Learned noise covariance*: Calibrating $\Sigma_{\text{noise}}$ from real sensor data (LiDAR, camera, or radar) to replace the synthetic noise model used in this study.
- *Temporal conflict classification*: Replacing the instantaneous geometric classifier with a recurrent model that uses frame-to-frame state transitions to disambiguate kinematically similar conflict types (particularly RIGHT\_OF\_WAY vs BROADSIDE).
- *Threshold adaptation*: Learning the PoNM decision threshold $\tau$ from labelled naturalistic data using proper scoring rule minimisation to achieve calibrated Bayesian operating points.
- *Real-world dataset validation*: Evaluating the complete pipeline on public near-miss datasets (e.g., inD, highD, DADA-2000) to quantify generalisation from the synthetic evaluation environment.

The simulator, algorithm implementations, and evaluation framework are designed for reproducibility and are made available to support future benchmarking of near-miss prediction methods.
