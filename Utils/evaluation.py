"""
Evaluation metrics for near-miss prediction algorithm.

Computes standard classification metrics and time-based performance measures.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Sources.scenario_types import FrameData
from Algorithm.near_miss_predictor import PredictionResult, ScenarioPrediction
from Utils.config import EvaluationConfig, RiskLevel


@dataclass
class ConfusionMatrix:
    """Confusion matrix for binary classification."""
    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    
    @property
    def total(self) -> int:
        return self.true_positives + self.true_negatives + self.false_positives + self.false_negatives
    
    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.total
    
    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        if denom == 0:
            return 0.0
        return self.true_positives / denom
    
    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        if denom == 0:
            return 0.0
        return self.true_positives / denom
    
    @property
    def f1_score(self) -> float:
        p, r = self.precision, self.recall
        if p + r == 0:
            return 0.0
        return 2 * p * r / (p + r)
    
    @property
    def false_positive_rate(self) -> float:
        denom = self.false_positives + self.true_negatives
        if denom == 0:
            return 0.0
        return self.false_positives / denom
    
    @property
    def false_negative_rate(self) -> float:
        denom = self.false_negatives + self.true_positives
        if denom == 0:
            return 0.0
        return self.false_negatives / denom
    
    def to_dict(self) -> Dict:
        return {
            'true_positives': self.true_positives,
            'true_negatives': self.true_negatives,
            'false_positives': self.false_positives,
            'false_negatives': self.false_negatives,
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'false_positive_rate': self.false_positive_rate,
            'false_negative_rate': self.false_negative_rate
        }


@dataclass
class EvaluationResults:
    """Complete evaluation results."""
    # Basic metrics
    confusion_matrix: ConfusionMatrix = field(default_factory=ConfusionMatrix)
    
    # Per-scenario metrics
    scenario_results: Dict[int, Dict] = field(default_factory=dict)
    
    # Temporal metrics
    detection_times: List[float] = field(default_factory=list)  # Time before event when detected
    mean_detection_time: float = 0.0
    std_detection_time: float = 0.0
    
    # Risk level distribution
    risk_distribution: Dict[str, int] = field(default_factory=dict)
    
    # Conflict type distribution
    conflict_distribution: Dict[str, int] = field(default_factory=dict)
    
    # SSM statistics
    ttc_stats: Dict[str, float] = field(default_factory=dict)
    drac_stats: Dict[str, float] = field(default_factory=dict)
    
    # Overall summary
    total_scenarios: int = 0
    total_frames: int = 0
    total_predictions: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'confusion_matrix': self.confusion_matrix.to_dict(),
            'scenario_results': self.scenario_results,
            'detection_times': self.detection_times,
            'mean_detection_time': self.mean_detection_time,
            'std_detection_time': self.std_detection_time,
            'risk_distribution': self.risk_distribution,
            'conflict_distribution': self.conflict_distribution,
            'ttc_stats': self.ttc_stats,
            'drac_stats': self.drac_stats,
            'total_scenarios': self.total_scenarios,
            'total_frames': self.total_frames,
            'total_predictions': self.total_predictions
        }


class Evaluator:
    """Evaluator for near-miss prediction algorithm."""
    
    def __init__(self, config: EvaluationConfig = None):
        self.config = config or EvaluationConfig()
    
    def extract_ground_truth(self, dataset: Dict[int, List[FrameData]]) -> Dict[int, List[Dict]]:
        """Extract ground truth labels from dataset.
        
        Args:
            dataset: Dictionary mapping scenario_id to frames
            
        Returns:
            Dictionary mapping scenario_id to list of ground truth events
        """
        ground_truth = {}
        
        for scenario_id, frames in dataset.items():
            events = []
            for frame in frames:
                for event in frame.ground_truth_events:
                    event_copy = event.copy()
                    event_copy['frame_id'] = frame.frame_id
                    event_copy['timestamp'] = frame.timestamp
                    events.append(event_copy)
            ground_truth[scenario_id] = events
        
        return ground_truth
    
    def evaluate_scenario(self, scenario_pred: ScenarioPrediction,
                         ground_truth_events: List[Dict]) -> Dict:
        """Evaluate predictions for a single scenario.
        
        Args:
            scenario_pred: Prediction results for scenario
            ground_truth_events: Ground truth events for scenario
            
        Returns:
            Dictionary with evaluation metrics
        """
        # Determine if scenario has actual near-miss
        has_actual_near_miss = len(ground_truth_events) > 0 and any(
            e.get('type') == 'near_miss' for e in ground_truth_events
        )
        
        # Determine if prediction detected near-miss
        prediction_detected = scenario_pred.near_miss_detected
        
        # Classification result
        if has_actual_near_miss and prediction_detected:
            result_type = 'true_positive'
        elif not has_actual_near_miss and not prediction_detected:
            result_type = 'true_negative'
        elif not has_actual_near_miss and prediction_detected:
            result_type = 'false_positive'
        else:
            result_type = 'false_negative'
        
        # Calculate detection time (for true positives)
        detection_time = None
        if result_type == 'true_positive' and ground_truth_events:
            # Find actual event time
            event_times = [e.get('time', e.get('timestamp', 0)) for e in ground_truth_events]
            actual_event_time = min(event_times) if event_times else 0
            
            # Detection was at first_detection_time
            if scenario_pred.first_detection_time is not None:
                detection_time = actual_event_time - scenario_pred.first_detection_time
        
        # Collect prediction statistics
        all_ttc = [p.ttc for p in scenario_pred.predictions if p.ttc is not None]
        all_drac = [p.drac for p in scenario_pred.predictions if p.drac is not None]
        
        return {
            'scenario_id': scenario_pred.scenario_id,
            'has_actual_near_miss': has_actual_near_miss,
            'prediction_detected': prediction_detected,
            'result_type': result_type,
            'detection_time': detection_time,
            'max_risk_level': scenario_pred.max_risk_level.name,
            'num_predictions': len(scenario_pred.predictions),
            'num_near_miss_predictions': scenario_pred.summary.get('total_near_misses', 0),
            'min_ttc': min(all_ttc) if all_ttc else None,
            'max_drac': max(all_drac) if all_drac else None
        }
    
    def evaluate_dataset(self, predictions: Dict[int, ScenarioPrediction],
                        dataset: Dict[int, List[FrameData]]) -> EvaluationResults:
        """Evaluate predictions against entire dataset.
        
        Args:
            predictions: Dictionary mapping scenario_id to ScenarioPrediction
            dataset: Dictionary mapping scenario_id to frames (for ground truth)
            
        Returns:
            EvaluationResults
        """
        results = EvaluationResults()
        
        # Extract ground truth
        ground_truth = self.extract_ground_truth(dataset)
        
        # Initialize counters
        cm = ConfusionMatrix()
        detection_times = []
        all_ttc = []
        all_drac = []
        risk_counts = defaultdict(int)
        conflict_counts = defaultdict(int)
        
        # Evaluate each scenario
        for scenario_id, scenario_pred in predictions.items():
            gt_events = ground_truth.get(scenario_id, [])
            
            scenario_result = self.evaluate_scenario(scenario_pred, gt_events)
            results.scenario_results[scenario_id] = scenario_result
            
            # Update confusion matrix
            if scenario_result['result_type'] == 'true_positive':
                cm.true_positives += 1
            elif scenario_result['result_type'] == 'true_negative':
                cm.true_negatives += 1
            elif scenario_result['result_type'] == 'false_positive':
                cm.false_positives += 1
            else:
                cm.false_negatives += 1
            
            # Collect detection time
            if scenario_result['detection_time'] is not None:
                detection_times.append(scenario_result['detection_time'])
            
            # Collect SSM values
            for pred in scenario_pred.predictions:
                if pred.ttc is not None:
                    all_ttc.append(pred.ttc)
                if pred.drac is not None:
                    all_drac.append(pred.drac)
                
                risk_counts[pred.risk_level.name] += 1
                conflict_counts[pred.conflict_type.name] += 1
            
            results.total_frames += scenario_pred.summary.get('total_frames', 0)
            results.total_predictions += len(scenario_pred.predictions)
        
        # Finalize results
        results.confusion_matrix = cm
        results.total_scenarios = len(predictions)
        results.detection_times = detection_times
        
        if detection_times:
            results.mean_detection_time = np.mean(detection_times)
            results.std_detection_time = np.std(detection_times)
        
        results.risk_distribution = dict(risk_counts)
        results.conflict_distribution = dict(conflict_counts)
        
        if all_ttc:
            results.ttc_stats = {
                'min': float(np.min(all_ttc)),
                'max': float(np.max(all_ttc)),
                'mean': float(np.mean(all_ttc)),
                'std': float(np.std(all_ttc))
            }
        
        if all_drac:
            results.drac_stats = {
                'min': float(np.min(all_drac)),
                'max': float(np.max(all_drac)),
                'mean': float(np.mean(all_drac)),
                'std': float(np.std(all_drac))
            }
        
        return results
    
    def generate_report(self, results: EvaluationResults) -> str:
        """Generate human-readable evaluation report.
        
        Args:
            results: Evaluation results
            
        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("NEAR-MISS PREDICTION EVALUATION REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Scenarios: {results.total_scenarios}")
        lines.append(f"Total Frames: {results.total_frames}")
        lines.append(f"Total Predictions: {results.total_predictions}")
        lines.append("")
        
        # Confusion Matrix
        cm = results.confusion_matrix
        lines.append("CONFUSION MATRIX")
        lines.append("-" * 40)
        lines.append(f"                    Predicted")
        lines.append(f"                 Near-Miss  Safe")
        lines.append(f"Actual Near-Miss    {cm.true_positives:5d}    {cm.false_negatives:5d}")
        lines.append(f"Actual Safe         {cm.false_positives:5d}    {cm.true_negatives:5d}")
        lines.append("")
        
        # Performance Metrics
        lines.append("PERFORMANCE METRICS")
        lines.append("-" * 40)
        lines.append(f"Accuracy:           {cm.accuracy:.4f}")
        lines.append(f"Precision:          {cm.precision:.4f}")
        lines.append(f"Recall:             {cm.recall:.4f}")
        lines.append(f"F1 Score:           {cm.f1_score:.4f}")
        lines.append(f"False Positive Rate:{cm.false_positive_rate:.4f}")
        lines.append(f"False Negative Rate:{cm.false_negative_rate:.4f}")
        lines.append("")
        
        # Detection Time
        if results.detection_times:
            lines.append("DETECTION TIME (seconds before event)")
            lines.append("-" * 40)
            lines.append(f"Mean: {results.mean_detection_time:.3f}s")
            lines.append(f"Std:  {results.std_detection_time:.3f}s")
            lines.append(f"Min:  {min(results.detection_times):.3f}s")
            lines.append(f"Max:  {max(results.detection_times):.3f}s")
            lines.append("")
        
        # Risk Distribution
        lines.append("RISK LEVEL DISTRIBUTION")
        lines.append("-" * 40)
        for level, count in sorted(results.risk_distribution.items()):
            lines.append(f"{level:15s}: {count:6d}")
        lines.append("")
        
        # SSM Statistics
        if results.ttc_stats:
            lines.append("TTC STATISTICS (seconds)")
            lines.append("-" * 40)
            lines.append(f"Min:  {results.ttc_stats['min']:.3f}")
            lines.append(f"Max:  {results.ttc_stats['max']:.3f}")
            lines.append(f"Mean: {results.ttc_stats['mean']:.3f}")
            lines.append(f"Std:  {results.ttc_stats['std']:.3f}")
            lines.append("")
        
        if results.drac_stats:
            lines.append("DRAC STATISTICS (m/s²)")
            lines.append("-" * 40)
            lines.append(f"Min:  {results.drac_stats['min']:.3f}")
            lines.append(f"Max:  {results.drac_stats['max']:.3f}")
            lines.append(f"Mean: {results.drac_stats['mean']:.3f}")
            lines.append(f"Std:  {results.drac_stats['std']:.3f}")
            lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def save_results(self, results: EvaluationResults, 
                    base_path: str = None) -> Tuple[str, str]:
        """Save evaluation results to files.
        
        Args:
            results: Evaluation results
            base_path: Base path for output files
            
        Returns:
            Tuple of (json_path, report_path)
        """
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'Results'
            )
        
        os.makedirs(base_path, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON
        json_path = os.path.join(base_path, f'evaluation_{timestamp}.json')
        with open(json_path, 'w') as f:
            json.dump(results.to_dict(), f, indent=2, default=str)
        
        # Save report
        report_path = os.path.join(base_path, f'evaluation_{timestamp}.txt')
        with open(report_path, 'w') as f:
            f.write(self.generate_report(results))
        
        return json_path, report_path
