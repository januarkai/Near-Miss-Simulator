"""
Robustness Study Script.

This script evaluates how the algorithm performs under varying levels of sensor noise.
This demonstrates the robustness of the system and provides non-trivial metrics.
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import copy
from typing import Dict, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Sources.data_generator import SyntheticDataGenerator
from Algorithm.near_miss_predictor import NearMissPredictor
from Algorithm.baseline_predictor import DistancePredictor
from Utils.evaluation import Evaluator

def inject_noise(dataset: Dict, pos_std: float, vel_std: float):
    """Injects Gaussian noise into the dataset observation."""
    noisy_dataset = copy.deepcopy(dataset)
    rng = np.random.default_rng(42)
    
    for scenario_id, frames in noisy_dataset.items():
        for frame in frames:
            for obj in frame.objects:
                # Add noise to position
                obj.x += rng.normal(0, pos_std)
                obj.y += rng.normal(0, pos_std)
                # Add noise to velocity
                obj.vx += rng.normal(0, vel_std)
                obj.vy += rng.normal(0, vel_std)
    return noisy_dataset

def run_study():
    print("Generating Ground Truth Dataset...")
    generator = SyntheticDataGenerator()
    seed = 123
    num_scenarios = 50
    # Generate clean data
    clean_dataset = generator.generate_dataset(num_scenarios, seed)
    
    # Define noise levels to test
    # (Position Error Std Dev in meters, Velocity Error Std Dev in m/s)
    noise_levels = [
        (0.0, 0.0),   # Perfect
        (0.2, 0.1),   # High Precision Sensors
        (0.5, 0.5),   # Standard Sensors
        (1.0, 1.0),   # Noisy Sensors
        (2.0, 2.0)    # Poor / Adverse Weather
    ]
    
    evaluator = Evaluator()
    results_summary = []
    
    print(f"\nRunning Robustness Study on {num_scenarios} scenarios...")
    print(f"{'Algorithm':<20} | {'Noise (Pos/Vel)':<15} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10}")
    print("-" * 80)
    
    algorithms = [
        ("Rule-Based SSM", NearMissPredictor()),
        ("Baseline (Dist)", DistancePredictor())
    ]
    
    for name, algo in algorithms:
        for pos_std, vel_std in noise_levels:
            # 1. Create Noisy Input
            noisy_input = inject_noise(clean_dataset, pos_std, vel_std)
            
            # 2. Run Prediction (Algorithm sees NOISY data)
            predictions = {}
            for s_id, frames in noisy_input.items():
                predictions[s_id] = algo.predict_scenario(s_id, frames)
            
            # 3. Evaluate (Compare Prediction against CLEAN Ground Truth)
            # This simulates real world: sensors are noisy, but reality is absolute.
            results = evaluator.evaluate_dataset(predictions, clean_dataset)
            
            cm = results.confusion_matrix
            print(f"{name:<20} | {pos_std}/{vel_std:<13} | {cm.precision:.<10.3f} | {cm.recall:.<10.3f} | {cm.f1_score:.<10.3f}")
            
            results_summary.append({
                'algorithm': name,
                'noise_pos': pos_std,
                'precision': cm.precision,
                'recall': cm.recall,
                'f1': cm.f1_score
            })
            
    print("\nStudy Complete.")

if __name__ == "__main__":
    run_study()
