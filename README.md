# Deterministic Near-Miss Prediction Simulator

A Bird's Eye View (BEV) based simulator for deterministic near-miss prediction using synthetic generated data.

## Overview

This simulator implements deterministic near-miss prediction algorithms based on Surrogate Safety Measures (SSMs) commonly used in traffic safety research:

- **TTC (Time to Collision)**: Time remaining until collision if current trajectories are maintained
- **DRAC (Deceleration Rate to Avoid Collision)**: Required deceleration to avoid collision
- **PET (Post-Encroachment Time)**: Time difference between two vehicles occupying the same space
- **MDR (Minimum Distance Ratio)**: Ratio of actual distance to safe minimum distance

It features a **Modular Algorithm System** allowing researchers to plug-in and test different near-miss detection logics dynamically via the GUI.

## Features

1. **Synthetic Data Generation**: Generate synthetic tracked object data with configurable parameters
2. **Custom Scenario Editor**: Create specific traffic scenarios frame-by-frame with physics-based object interpolation.
3. **Modular Algorithm Selector**: Switch between different prediction algorithms at runtime.
4. **Data Export/Import**: Save and load synthetic data in CSV format
5. **Deterministic Near-Miss Prediction**: Rule-based prediction using multiple SSMs
6. **BEV Visualization**: Real-time Bird's Eye View visualization of tracked objects
7. **Evaluation Metrics**: Comprehensive evaluation of prediction algorithm performance

## Project Structure

```
Simulator/
├── Algorithm/
│   ├── __init__.py
│   ├── base_algorithm.py      # Abstract base class for algorithms
│   ├── registry.py            # Algorithm registration system
│   ├── ssm_calculator.py      # Surrogate Safety Measures calculations
│   ├── near_miss_predictor.py # Standard Rule-Based SSM implementation
│   └── trajectory_model.py    # Constant velocity trajectory model
├── Dataset/
│   └── (generated CSV files)
├── Results/
│   └── (evaluation results and visualizations)
├── Sources/
│   ├── __init__.py
│   ├── data_generator.py      # Synthetic data generation
│   ├── data_loader.py         # CSV import/export functionality
│   └── scenario_types.py      # Predefined scenario configurations
├── Utils/
│   ├── __init__.py
│   ├── config.py              # Configuration parameters
│   ├── visualization.py       # BEV visualization utilities
│   └── evaluation.py          # Evaluation metrics calculation
├── main.py                    # Main entry point with GUI
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

```bash
cd Code/Simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Run the GUI Simulator
```bash
python3 main.py
```

### Command Line Options
```bash
# Generate synthetic data
python3 main.py --generate --scenarios 10 --output Dataset/synthetic_data.csv

# Run prediction on existing data
python3 main.py --input Dataset/synthetic_data.csv --evaluate

# Run with visualization
python3 main.py --input Dataset/synthetic_data.csv --visualize
```

## Tracked Object Attributes

Each tracked object in the synthetic data contains:

| Attribute | Description | Unit |
|-----------|-------------|------|
| `frame_id` | Time step / frame number | - |
| `object_id` | Unique identifier for tracked object | - |
| `x` | Longitudinal position (BEV) | meters |
| `y` | Lateral position (BEV) | meters |
| `vx` | Longitudinal velocity (relative to ego) | m/s |
| `vy` | Lateral velocity (relative to ego) | m/s |
| `length` | Object length | meters |
| `width` | Object width | meters |
| `object_class` | Object type (car, truck, pedestrian, etc.) | - |

## Deterministic Near-Miss Prediction Algorithm

The algorithm uses a multi-criteria approach:

1. **Trajectory Prediction**: Constant velocity model for short-term prediction
2. **Conflict Detection**: Check for potential path intersections
3. **SSM Calculation**: Compute TTC, DRAC, PET, MDR
4. **Risk Classification**: Apply threshold-based rules to classify risk level

### Risk Levels

- **Safe**: No imminent collision risk
- **Warning**: Potential risk, monitoring required
- **Near-Miss**: High risk, evasive action may be needed
- **Collision**: Collision is imminent or occurring

### Thresholds (configurable)

| SSM | Safe | Warning | Near-Miss | Collision |
|-----|------|---------|-----------|-----------|
| TTC | >4s | 2-4s | 1-2s | <1s |
| DRAC | <2 m/s² | 2-4 m/s² | 4-6 m/s² | >6 m/s² |
| PET | >2s | 1-2s | 0.5-1s | <0.5s |
| MDR | >1.5 | 1.0-1.5 | 0.5-1.0 | <0.5 |

## Evaluation Metrics

- **Precision**: Correctly predicted near-misses / All predicted near-misses
- **Recall**: Correctly predicted near-misses / All actual near-misses
- **F1 Score**: Harmonic mean of precision and recall
- **False Positive Rate**: False predictions / All safe situations
- **Time to Detection**: Average time before actual near-miss event

## Scenario Editor

The **Scenario Editor** allows for precise creation of test cases:
1. **Add Frame**: Click to create a new frame.
   - **Physics Mode**: Based on the `FPS` setting, objects will automatically move to their predicted positions based on their `Vx` and `Vy`.
   - **Manual Mode**: Manually adjust positions for specific edge cases.
2. **Add Object**: Define object properties (position, size, velocity, class).
3. **Controls**:
   - `Save Scenario`: Saves the current sequence to a JSON file.
   - `FPS`: Controls the simulation time-step delta (default: 10 FPS = 0.1s step).

## Developer Guide: Adding Custom Algorithms

The simulator uses a registry-based system to load prediction algorithms. To add a new method:

1. Create a new file in `Algorithm/` (e.g., `my_algorithm.py`).
2. Inherit from `NearMissAlgorithm`.
3. Implement `predict_scenario`.
4. Register the class using the `@AlgorithmRegistry.register` decorator.

**Example:**

```python
# Algorithm/my_algorithm.py
from .base_algorithm import NearMissAlgorithm
from .registry import AlgorithmRegistry

@AlgorithmRegistry.register
class MyCustomPredictor(NearMissAlgorithm):
    @property
    def name(self) -> str:
        return "My Custom Logic (v1)"

    def predict_scenario(self, scenario_df, **kwargs):
        # Your custom logic here
        results = []
        for frame_id, group in scenario_df.groupby('frame_id'):
            # ... do prediction ...
            pass
        return results
```

The new algorithm will automatically appear in the GUI dropdown menu next time you run the application.

## Author

January Kailani Suaeb - Master's Thesis Research
