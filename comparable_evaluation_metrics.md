# Unified Evaluation Framework for Deterministic vs. Stochastic Comparison

## 1. The Comparability Challenge

You correctly identified a critical scientific gap: **How to fairly compare a rigid Rule-Based system (Algorithm A) against a Probabilistic Monte Carlo system (Algorithm B)?**

*   **Algorithm A (Current)** outputs a binary decision: `Safe` (0) or `Near-Miss` (1).
*   **Algorithm B (Proposed)** outputs a continuous probability: `PoNM` $\in [0, 1]$.
*   **Ground Truth** is binary: `Actual Event` (1) or `None` (0).

If we simply threshold Algorithm B (e.g., $P > 0.5 \implies 1$), we lose its novelty (the expression of uncertainty). If we don't, we can't calculate F1 Score.

## 2. Solution: Proper Scoring Rules

To resolve this, we must shift from "Classification Metrics" (Accuracy/F1) to **"Probabilistic Scoring Rules"**. These metrics penalize *overconfidence* in wrong answers, which is exactly where Deterministic algorithms fail and Stochastic ones shine.

### Metric 1: The Brier Score (BS)
This is the "Mean Squared Error" for predictions. It is the gold standard for comparing binary and probabilistic forecasts.

$$ BS = \frac{1}{N} \sum_{i=1}^{N} (p_i - o_i)^2 $$

*   $p_i$: The predicted probability of near-miss.
    *   **Deterministic Algo**: $p_i$ is always exactly $0.0$ or $1.0$.
    *   **Stochastic Algo**: $p_i$ is the calculated probability (e.g., $0.72$).
*   $o_i$: The actual outcome ($1$ if near-miss occurred, $0$ if not).

**Why it works:**
*   **Scenario:** A chaotic situation is 60% likely to crash. Outcome: No Crash (0).
*   **Deterministic Algo:** Predicts "Crash" (1.0). Error = $(1.0 - 0)^2 = 1.0$ (High penalty for false alarm).
*   **Stochastic Algo:** Predicts "Risk" (0.6). Error = $(0.6 - 0)^2 = 0.36$ (Lower penalty).
*   **Result:** The Stochastic algorithm wins (lower BS) because it was "less wrong."

### Metric 2: Area Under ROC Curve (AUROC)
Instead of picking a single threshold for the Stochastic algorithm, we evaluate its ability to rank scenarios from least to most dangerous.

*   **Stochastic Algo**: Generates a full curve by varying the detection threshold from 0.0 to 1.0. We calculate the area under this curve.
*   **Deterministic Algo**: Represents a single point on this plot.
*   **Comparison**: If the Stochastic curve passes *above* the Deterministic point, it is scientifically superior across different sensitivity requirements.

### Metric 3: Time-Integrated Risk (Novelty metric)
Instead of evaluating a single frame instant (which is jittery), integrate the risk score over the duration of the scenario.

$$ Risk_{accumulated} = \int_{t=0}^{T} Risk(t) \cdot dt $$

*   **Deterministic**: Tends to be a "Step Function" (0 -> 1 -> 0).
*   **Stochastic**: Smooth curve (0 -> 0.2 -> 0.8 -> 0.3).
*   **Novelty**: Show that Stochastic Risk provides a **early warning signal** (non-zero integral) seconds before the Deterministic threshold is breached.

## 3. Robustness Consistency (RC)
This metric specifically targets the "Noise" gap identified.

Define $M$ as a standard metric (e.g., F1 Score). Calculate $M$ at varying noise levels ($\sigma$).

$$ RC = \frac{dM}{d\sigma} $$

*   Plot F1 Score vs. Sensor Noise Level.
*   **Deterministic**: Will likely show a steep drop-off (Step).
*   **Stochastic**: Should show a gradual decline (Gentle slope).
*   **Comparison**: The "Novelty" is the integral of performance retention under noise.

## 4. Summary for Publication

To support your publication, add a section **"Comparative Evaluation Framework"** that explicitly defines:

1.  **Brier Score** (showing Calibration accuracy).
2.  **Robustness Curve** (showing F1 stability under noise).
3.  **Detection Latency Distribution** (showing how early the probability rises vs when the binary flag touches 1).

This essentially creates a **mathematically rigorous comparison** where the Deterministic algorithm is simply a special case of the Probabilistic one (where variance = 0), allowing for direct "apples-to-apples" comparison.
