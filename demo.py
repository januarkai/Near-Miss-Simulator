#!/usr/bin/env python3
"""
Demo script for Near-Miss Prediction Simulator.

This script demonstrates the main features:
1. Synthetic data generation
2. CSV export/import
3. Deterministic near-miss prediction
4. Evaluation metrics

Run with: python3 demo.py
"""

import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Sources.data_generator import SyntheticDataGenerator
from Sources.data_loader import DataLoader
from Sources.scenario_types import ScenarioType
from Algorithm.near_miss_predictor import NearMissPredictor
from Algorithm.ssm_calculator import SSMCalculator
from Utils.config import SSMThresholds
from Utils.evaluation import Evaluator


def main():
    print("=" * 60)
    print("Near-Miss Prediction Simulator - Demo")
    print("=" * 60)
    
    # 1. Generate synthetic data
    print("\n[1] Generating Synthetic Data...")
    print("-" * 40)
    
    generator = SyntheticDataGenerator()
    generator.set_seed(42)
    
    # Generate 20 scenarios
    dataset = generator.generate_dataset(20)
    
    total_frames = sum(len(frames) for frames in dataset.values())
    total_objects = sum(
        sum(len(f.objects) for f in frames)
        for frames in dataset.values()
    )
    
    print(f"Generated {len(dataset)} scenarios")
    print(f"Total frames: {total_frames}")
    print(f"Total object observations: {total_objects}")
    
    # Show scenario distribution
    print("\nScenario examples:")
    for scenario_id in list(dataset.keys())[:3]:
        frames = dataset[scenario_id]
        print(f"  Scenario {scenario_id}: {len(frames)} frames, "
              f"{len(frames[0].objects)} initial objects")
    
    # 2. Export to CSV
    print("\n[2] Exporting Data to CSV...")
    print("-" * 40)
    
    loader = DataLoader()
    csv_path = loader.export_to_csv(dataset, 'demo_data.csv')
    print(f"Exported to: {csv_path}")
    
    # Show file info
    file_size = os.path.getsize(csv_path)
    print(f"File size: {file_size / 1024:.1f} KB")
    
    # 3. Import from CSV
    print("\n[3] Importing Data from CSV...")
    print("-" * 40)
    
    imported_dataset = loader.import_from_csv('demo_data.csv')
    print(f"Imported {len(imported_dataset)} scenarios")
    
    # 4. Run Near-Miss Prediction
    print("\n[4] Running Near-Miss Prediction Algorithm...")
    print("-" * 40)
    
    # Configure predictor with custom thresholds
    custom_thresholds = SSMThresholds(
        ttc_near_miss=1.5,  # TTC below 1.5s = near-miss
        drac_near_miss=5.0,  # DRAC above 5 m/s² = near-miss
        mdr_near_miss=0.6    # MDR below 0.6 = near-miss
    )
    
    predictor = NearMissPredictor(thresholds=custom_thresholds)
    predictions = predictor.predict_dataset(dataset)
    
    # Summarize predictions
    nm_scenarios = sum(1 for p in predictions.values() if p.near_miss_detected)
    total_nm_events = sum(p.summary.get('total_near_misses', 0) for p in predictions.values())
    
    print(f"Scenarios with near-miss: {nm_scenarios}/{len(predictions)}")
    print(f"Total near-miss events detected: {total_nm_events}")
    
    # Show example predictions
    print("\nExample predictions:")
    for scenario_id in list(predictions.keys())[:3]:
        pred = predictions[scenario_id]
        print(f"  Scenario {scenario_id}: "
              f"Near-miss={'Yes' if pred.near_miss_detected else 'No'}, "
              f"Max risk={pred.max_risk_level.name}")
    
    # 5. Detailed SSM Analysis for one scenario
    print("\n[5] Detailed SSM Analysis (Scenario 0, Frame 0)...")
    print("-" * 40)
    
    ssm_calc = SSMCalculator(custom_thresholds)
    sample_frame = dataset[0][50] if len(dataset[0]) > 50 else dataset[0][-1]
    
    for obj in sample_frame.objects[:3]:
        ssm_result = ssm_calc.calculate_all_ssm(sample_frame.ego, obj)
        
        print(f"\nObject {obj.object_id} ({obj.object_class}):")
        print(f"  Position: ({obj.x:.1f}, {obj.y:.1f}) m")
        print(f"  Velocity: ({obj.vx:.1f}, {obj.vy:.1f}) m/s")
        print(f"  Distance: {ssm_result.distance:.1f} m")
        print(f"  TTC: {ssm_result.ttc:.2f}s" if ssm_result.ttc else "  TTC: N/A")
        print(f"  DRAC: {ssm_result.drac:.2f} m/s²" if ssm_result.drac else "  DRAC: N/A")
        print(f"  MDR: {ssm_result.mdr:.2f}" if ssm_result.mdr else "  MDR: N/A")
        print(f"  Risk Level: {ssm_result.risk_level.name}")
    
    # 6. Run Evaluation
    print("\n[6] Running Evaluation...")
    print("-" * 40)
    
    evaluator = Evaluator()
    results = evaluator.evaluate_dataset(predictions, dataset)
    
    # Print metrics
    cm = results.confusion_matrix
    print("\nConfusion Matrix:")
    print(f"  True Positives:  {cm.true_positives}")
    print(f"  True Negatives:  {cm.true_negatives}")
    print(f"  False Positives: {cm.false_positives}")
    print(f"  False Negatives: {cm.false_negatives}")
    
    print("\nPerformance Metrics:")
    print(f"  Accuracy:  {cm.accuracy:.4f}")
    print(f"  Precision: {cm.precision:.4f}")
    print(f"  Recall:    {cm.recall:.4f}")
    print(f"  F1 Score:  {cm.f1_score:.4f}")
    
    if results.detection_times:
        print(f"\nDetection Time Statistics:")
        print(f"  Mean: {results.mean_detection_time:.2f}s before event")
        print(f"  Std:  {results.std_detection_time:.2f}s")
    
    # Save evaluation results
    json_path, report_path = evaluator.save_results(results)
    print(f"\nResults saved to:")
    print(f"  {json_path}")
    print(f"  {report_path}")
    
    # 7. Print full report
    print("\n[7] Full Evaluation Report")
    print("=" * 60)
    print(evaluator.generate_report(results))
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    print("\nTo run the GUI simulator:")
    print("  python3 main.py")
    print("\nTo run with command line:")
    print("  python3 main.py --generate --scenarios 50 --evaluate")


if __name__ == '__main__':
    main()
