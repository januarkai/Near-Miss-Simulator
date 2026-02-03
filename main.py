"""
Near-Miss Prediction Simulator
==============================

Main entry point for the deterministic near-miss prediction simulator.

Usage:
    # Run GUI
    python3 main.py
    
    # Generate synthetic data
    python3 main.py --generate --scenarios 50 --output data.csv
    
    # Run prediction on existing data  
    python3 main.py --input data.csv --evaluate
    
    # Full pipeline with visualization
    python3 main.py --input data.csv --visualize
"""

import argparse
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Sources.data_generator import SyntheticDataGenerator
from Sources.data_loader import DataLoader
from Algorithm.near_miss_predictor import NearMissPredictor
from Utils.config import DEFAULT_SIMULATION_CONFIG, DEFAULT_DATA_GENERATOR_CONFIG
from Utils.evaluation import Evaluator


def generate_data(args):
    """Generate synthetic data."""
    print(f"Generating {args.scenarios} scenarios...")
    
    generator = SyntheticDataGenerator()
    
    if args.seed:
        generator.set_seed(args.seed)
    
    dataset = generator.generate_dataset(args.scenarios, args.seed)
    
    # Export to CSV
    loader = DataLoader()
    output_path = args.output or 'synthetic_data.csv'
    filepath = loader.export_to_csv(dataset, output_path)
    
    print(f"Data saved to: {filepath}")
    return dataset


def run_prediction(dataset, verbose=True):
    """Run near-miss prediction on dataset."""
    if verbose:
        print(f"Running prediction on {len(dataset)} scenarios...")
    
    predictor = NearMissPredictor()
    predictions = predictor.predict_dataset(dataset)
    
    if verbose:
        nm_count = sum(1 for p in predictions.values() if p.near_miss_detected)
        print(f"Near-misses detected: {nm_count}/{len(predictions)}")
    
    return predictions


def run_evaluation(predictions, dataset, save_results=True):
    """Run evaluation on predictions."""
    print("Running evaluation...")
    
    evaluator = Evaluator()
    results = evaluator.evaluate_dataset(predictions, dataset)
    
    # Print summary
    cm = results.confusion_matrix
    print("\n=== Evaluation Results ===")
    print(f"Accuracy:  {cm.accuracy:.4f}")
    print(f"Precision: {cm.precision:.4f}")
    print(f"Recall:    {cm.recall:.4f}")
    print(f"F1 Score:  {cm.f1_score:.4f}")
    
    if save_results:
        json_path, report_path = evaluator.save_results(results)
        print(f"\nResults saved to:")
        print(f"  JSON: {json_path}")
        print(f"  Report: {report_path}")
    
    return results


def run_gui():
    """Launch the GUI application."""
    from gui_app import main as gui_main
    gui_main()


def main():
    parser = argparse.ArgumentParser(
        description="Near-Miss Prediction Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Mode selection
    parser.add_argument('--gui', action='store_true', default=True,
                       help='Launch GUI mode (default)')
    parser.add_argument('--cli', action='store_true',
                       help='Run in CLI mode')
    
    # Data generation
    parser.add_argument('--generate', action='store_true',
                       help='Generate synthetic data')
    parser.add_argument('--scenarios', type=int, default=10,
                       help='Number of scenarios to generate')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    
    # I/O
    parser.add_argument('--input', type=str,
                       help='Input CSV file for prediction')
    parser.add_argument('--output', type=str,
                       help='Output CSV file for generated data')
    
    # Actions
    parser.add_argument('--evaluate', action='store_true',
                       help='Run evaluation after prediction')
    parser.add_argument('--visualize', action='store_true',
                       help='Open visualization after loading data')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.cli or args.generate or args.input:
        # CLI mode
        dataset = None
        
        # Generate or load data
        if args.generate:
            dataset = generate_data(args)
        elif args.input:
            print(f"Loading data from {args.input}...")
            loader = DataLoader()
            dataset = loader.import_from_csv(args.input)
            print(f"Loaded {len(dataset)} scenarios")
        
        if dataset is None:
            print("No data available. Use --generate or --input")
            return
        
        # Run prediction
        predictions = run_prediction(dataset)
        
        # Run evaluation if requested
        if args.evaluate:
            run_evaluation(predictions, dataset)
        
        # Open visualization if requested
        if args.visualize:
            run_gui()
    else:
        # GUI mode (default)
        run_gui()


if __name__ == '__main__':
    main()
