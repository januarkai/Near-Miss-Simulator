# Gap Analysis and Novelty Assessment

## 1. Introduction
This document analyzes the current state of the Simulator project relative to recent academic research (2021-2025) and proposes a novel hybrid methodology to enhance its scientific contribution.

## 2. Recent Related Work (2021-2025)

Based on a review of recent literature from IEEE, ScienceDirect, and MDPI, the following approaches dominate the field:

| Reference | Methodology | Contribution | Limitation |
| :--- | :--- | :--- | :--- |
| **Spatiotemporal GNNs (2022)** | Graph Neural Networks + LSTM for interaction modeling. | Captures latent interactions between vehicles (e.g., yielding behavior). | High inference cost; "Black Box" explainability. |
| **Hybrid CNN + SSM (2023)** | Deterministic SSMs filtered by CNN heatmaps. | Reduces false alarms by learning context from trajectory maps. | Requires extensive labeled heatmap datasets. |
| **Probabilistic TTC (2022)** | Modeled position as Gaussian distributions $\mathcal{N}(\mu, \sigma)$. | Outputs "Probability of TTC < Threshold" instead of binary safe/unsafe. | Sensitive to sensor covariance estimation accuracy. |
| **Potential Fields (2021)** | Virtual force fields representing risk energy. | Unifies different risk factors (mass, speed) into one continuum. | Difficult manual tuning of field coefficients. |
| **Adaptive SSMs (2024)** | Dynamic thresholds based on road friction/weather. | Reduces false positives in adverse weather. | Requires environmental metadata (friction) often unavailable. |

---

## 3. Gap Analysis of Current Project

The current simulator uses a **Deterministic Rule-Based SSM** approach.
*   **Method**: Predicts a single trajectory using a Constant Velocity Model.
*   **Decision**: Checks if `TTC < Threshold`.
*   **Gap**:
    1.  **Binary Rigidity**: A scenario with $TTC=1.51s$ is deemed "Safe", while $1.49s$ is "Risk", ignoring the inherent noise in sensor data.
    2.  **Ignored Uncertainty**: The `TrajectoryPredictor` calculates uncertainty, but the `SSMCalculator` ignores it, using only the mean position.
    3.  **Lack of "Tail Risk"**: In highly unpredictable scenarios (like the stochastic movement recently added), the "mean" trajectory might be safe, but a likely deviation could be fatal. The current system misses this.

---

## 4. Proposed Novelty: "Stochastic Monte Carlo SSM Fusion"

To elevate the research from a "basic implementation" to a "novel contribution," I propose implementing a **Hybrid Stochastic-Deterministic Algorithm**.

**Core Idea**: 
Instead of predicting **one** future state and calculating **one** SSM value, we will use **Monte Carlo Sampling** to generate a *distribution* of possible future states, calculate SSMs for all of them, and derive a **Probability of Near-Miss (PoNM)**.

### Methodology
1.  **Uncertainty Propagation**: 
    Leverage the existing Gaussian noise in `Sources/data_generator.py` (which creates the movement) to define the uncertainty model in the predictor.
    
2.  **fast-Monte Carlo Sampling (N=20-50)**:
    For every frame, instead of projecting one future point $(x_{t+k}, y_{t+k})$, we project $N$ points sampled from the uncertainty distribution:
    $$ P_{sample}^{(i)} \sim \mathcal{N}(P_{predicted}, \Sigma_{noise}) $$

3.  **Ensemble SSM Calculation**:
    Compute the SSM (e.g., TTC) for *each* of the $N$ samples against the Ego vehicle.
    $$ \{ TTC_1, TTC_2, ..., TTC_N \} $$

4.  **Probabilistic Risk Scoring**:
    Define the risk not as a binary switch, but as the *fraction of samples* that violate the safety threshold:
    $$ Risk = \frac{\sum_{i=1}^{N} \mathbb{1}(TTC_i < \tau)}{N} $$

### Scientific Contribution
*   **Bridging the Gap**: This method fuses the *interpretability* of SSMs (unlike black-box Neural Networks) with the *robustness* of probabilistic methods (unlike rigid rule-based systems).
*   **Robustness to Chaos**: It specifically addresses the "stochastic/unpredictable" nature of mixed traffic (the exact behavior you requested in the "stochastic move" prompt).
*   **Novel Eval Metric**: We can evaluate the algorithm using **"Risk Uncertainty"**—how confident is the system that a situation is safe?

---

## 5. Implementation Roadmap
1.  Modify `near_miss_predictor.py` to accept a `num_samples` parameter.
2.  Update `predict_single_object` to loop `N` times, adding slight Gaussian perturbations to `obj.x` and `obj.y` before calling `ssm_calculator`.
3.  Store the percentage of "unsafe" samples as `probability_of_conflict`.
4.  Update the evaluation report to show this probability.

This moves the paper title from *"A Rule-Based Simulator"* to *"**Probabilistic Risk Assessment in Stochastic Mixed-Traffic Environments using Ensemble Surrogate Safety Measures**"*.
