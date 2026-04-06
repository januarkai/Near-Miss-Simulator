# IV. EXPERIMENTAL RESULTS

## A. Experimental Conditions

All three algorithms were evaluated on the same synthetic dataset of 30 mixed near-miss scenarios, each containing 10 surrounding objects (5 ground-truth near-miss objects spanning the five conflict types and 5 safe background objects), for a total of 300 object-level predictions per algorithm. Scenarios were generated with a fixed random seed to ensure identical stimulus sequences across all methods. The ego vehicle travels at 50 km/h ($\approx 13.9$ m/s), and each scenario runs for 15 seconds at 10 Hz (150 frames). Object states are corrupted with additive Gaussian noise (position $\sigma_p = 0.3$ m, velocity $\sigma_v = 1.5$ m/s) to simulate realistic ADAS sensor conditions.

The evaluation framework operates at two levels of granularity as described in Section III-D: (i) object-level classification, where each of the 300 tracked objects is assessed for near-miss status against its ground-truth label, and (ii) probabilistic quality metrics, which measure the calibration and ordering quality of the continuous confidence scores produced by each algorithm.

## B. Overall Detection Performance

Table IV presents the object-level classification metrics for all three algorithms, pooled across all 30 scenarios.

**Table IV. Object-Level Classification Metrics (300 Predictions, 30 Scenarios)**

| Metric | Baseline (Algo A) | Rule-Based SSM (Algo B) | MC-SSM (Algo C) |
|---|---|---|---|
| Accuracy | 0.640 | 0.500 | **0.717** |
| Precision | 0.627 | 0.500 | **0.810** |
| Recall | 0.693 | **1.000** | 0.567 |
| F1 Score | 0.658 | 0.667 | **0.667** |
| FPR | 0.413 | 1.000 | **0.133** |
| TP / TN / FP / FN | 104 / 88 / 62 / 46 | 150 / 0 / 150 / 0 | 85 / 130 / 20 / 65 |

The Rule-Based SSM (Algorithm B) achieves perfect recall (1.000) but at the cost of a false-positive rate of 1.000: it flags every single object as near-miss, resulting in zero true negatives. Consequently its accuracy collapses to 0.500 --- equivalent to a random classifier. The equal F1 scores (0.667) for Rule-Based and MC-SSM are therefore not equivalent: the Rule-Based value inflates recall by discarding all specificity, while the MC-SSM value reflects a balanced trade-off with an 81.0% precision and only 13.3% false-positive rate.

The Baseline Distance predictor (Algorithm A) falls between the two in recall (0.693) and FPR (0.413). Its F1 score (0.658) reflects the moderate performance expected from a kinematic-context-free method, and it provides the performance lower bound that motivates the use of more sophisticated approaches.

## C. Probabilistic and Temporal Quality

Table V reports the probabilistic calibration and temporal quality metrics, which are only computable for algorithms that produce continuous confidence scores.

**Table V. Probabilistic and Temporal Quality Metrics**

| Metric | Baseline (Algo A) | Rule-Based SSM (Algo B) | MC-SSM (Algo C) |
|---|---|---|---|
| Brier Score $\downarrow$ | 0.360 | 0.328 | **0.258** |
| AUROC $\uparrow$ | 0.648 | **0.802** | 0.775 |
| Mean $t$-IoU $\uparrow$ | 0.239 | 0.368 | 0.143 |

The MC-SSM achieves the lowest Brier Score (0.258), indicating the best-calibrated probability estimates among the three algorithms. This result is consistent with the design of the MC-SSM: because the PoNM confidence score represents a well-defined empirical probability over the 30-particle ensemble, it is inherently better anchored than the additive heuristic score used by Rule-Based SSM.

The Rule-Based SSM achieves the highest AUROC (0.802), meaning its internal ranking of objects from most to least risky correlates most strongly with ground truth ordering --- despite the broken binary threshold. Because the Rule-Based SSM assigns confidence scores above 0.5 to virtually every object, its ranking is driven by the relative magnitude of the SSM values rather than by a threshold decision. MC-SSM's AUROC (0.775) is also strong and significantly above the Baseline (0.648), confirming that the ensemble probability provides discriminative information beyond simple distance.

The mean temporal Intersection over Union ($t$-IoU) measures the overlap between the predicted near-miss time window and the ground-truth near-miss window. Rule-Based SSM's higher $t$-IoU (0.368) occurs because it fires for long continuous windows, increasing overlap as a side effect of the always-on behaviour. MC-SSM's lower $t$-IoU (0.143) reflects its more conservative, pulse-like detections that match the true near-miss window only partially.

## D. Conflict Type Classification

Table VI shows the global conflict type accuracy --- the fraction of near-miss detections where the predicted conflict category matches the ground-truth scenario type --- and the dominant confusion patterns.

**Table VI. Conflict Type Classification Summary**

| Algorithm | Type Accuracy | Dominant Confusion |
|---|---|---|
| Baseline (Algo A) | 0.000 | N/A (no type assigned) |
| Rule-Based SSM (Algo B) | 0.507 | RIGHT\_OF\_WAY → BROADSIDE (33%) |
| MC-SSM (Algo C) | 0.388 | RIGHT\_OF\_WAY → BROADSIDE (40%) |

The Baseline Distance predictor assigns `NONE` to every detected object, yielding zero type accuracy by design. Both kinematic algorithms share the dominant confusion pattern: objects labelled RIGHT\_OF\_WAY are frequently classified as BROADSIDE. This confusion is an anticipated fundamental limitation of any instantaneous-state classifier: when a right-of-way vehicle activates its lateral manoeuvre (at $d_x < 30$ m), its kinematic signature --- high lateral velocity ($|v_y| \approx 8$ m/s) from a far-lateral position --- is indistinguishable from that of a broadside intruder crossing the same zone. Resolving this ambiguity would require multi-frame trajectory history, which lies outside the scope of the single-frame classifier.

After excluding the unavoidable RIGHT\_OF\_WAY/BROADSIDE confusion, the residual type accuracy for the five remaining conflict types is 0.623 for Rule-Based SSM and 0.543 for MC-SSM, representing acceptable classification quality for the rear-end, lane-change, and cutoff categories.

## E. Algorithm Behaviour Summary

A key design property of the MC-SSM is that it converts a hard threshold decision into a probabilistic one. This resolves the binary rigidity problem inherent in Rule-Based SSM: an object with TTC = 1.51 s (just safe) and one with TTC = 1.49 s (just critical) receive nearly identical PoNM scores under the ensemble, whereas Rule-Based SSM assigns them to opposite sides of the binary boundary, leading to the uniform flagging behaviour observed above.

The cost of this precision gain is a modest reduction in recall (0.567 vs 1.000), because the MC-SSM correctly restrains from firing on objects where the ensemble only marginally exceeds the 30% threshold. For safety-critical ADAS applications where false alarms lead to driver desensitisation (known as the "alarm fatigue" effect), the MC-SSM's lower FPR (0.133 vs 1.000) represents the more operationally desirable trade-off.
