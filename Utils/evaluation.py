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
    
    # Conflict Type Accuracy & Confusion Matrix (Sequence Level)
    type_confusion_matrix: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    mean_tiou: float = 0.0
    type_accuracy_global: float = 0.0
    
    # SSM statistics
    ttc_stats: Dict[str, float] = field(default_factory=dict)
    drac_stats: Dict[str, float] = field(default_factory=dict)
    
    # Proper Scoring Rules (Novel Metrics)
    brier_score: float = 0.0
    auroc: float = 0.0 # Area Under ROC Curve (requires storing probs)
    reliability_diagram: Dict = field(default_factory=dict) # Calibration curve points
    
    # Overall summary
    total_scenarios: int = 0
    total_frames: int = 0
    total_predictions: int = 0
    algorithm_name: str = "Unknown"
    
    def to_dict(self) -> Dict:
        return {
            'algorithm_name': self.algorithm_name,
            'confusion_matrix': self.confusion_matrix.to_dict(),
            'scenario_results': self.scenario_results,
            'mean_tiou': self.mean_tiou,
            'type_accuracy_global': self.type_accuracy_global,
            'type_confusion_matrix': self.type_confusion_matrix,
            'detection_times': self.detection_times,
            'mean_detection_time': self.mean_detection_time,
            'std_detection_time': self.std_detection_time,
            'risk_distribution': self.risk_distribution,
            'conflict_distribution': self.conflict_distribution,
            'ttc_stats': self.ttc_stats,
            'drac_stats': self.drac_stats,
            'brier_score': self.brier_score,
            'auroc': self.auroc,
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
                         ground_truth_events: List[Dict],
                         frames: List[FrameData] = None) -> Dict:
        """Evaluate predictions for a single scenario with object-level detail."""
        
        # 1. Determine Ground Truth per Object
        # We need to map Object ID -> Is Near Miss
        gt_object_status = {} # {obj_id: bool}
        gt_object_types = {}  # {obj_id: 'nm_side_swipe'}
        gt_intervals = defaultdict(list) # {obj_id: [(start_t, end_t, type)]}
        
        # Parse Ground Truth Events first to get precise intervals
        for evt in ground_truth_events:
            if 'object_id' in evt:
                oid = evt['object_id']
                t = evt['time']
                etype = evt['scenario_type']
                
                # Simple interval construction: assume single frame events merge
                # We will process frames for continuity if available, or just mark frames
                gt_intervals[oid].append((t, t, etype)) 
                gt_object_types[oid] = etype
        
        # Merge consecutive timestamps into intervals
        for oid in gt_intervals:
            timestamps = sorted([x[0] for x in gt_intervals[oid]])
            merged = []
            if timestamps:
                start = timestamps[0]
                curr = start
                for t in timestamps[1:]:
                    if t - curr > 0.15: # Gap > 1.5 * dt (assuming 0.1s dt)
                        merged.append((start, curr))
                        start = t
                    curr = t
                merged.append((start, curr))
            gt_intervals[oid] = merged

        if frames and len(frames) > 0:
            # Get object roles from first frame (assuming consistent ID/Role)
            first_frame_objs = frames[0].objects
            for obj in first_frame_objs:
                # Rule: 'nm_' prefix means Positive (Near Miss)
                is_positive = getattr(obj, 'is_risk_object', False) 
                if not is_positive: 
                     is_positive = obj.role.startswith('nm_') # Fallback
                
                gt_object_status[obj.object_id] = is_positive
                
                # If specific type known from role
                if is_positive and obj.object_id not in gt_object_types:
                     # Map role to type constants if possible
                     if obj.role == "nm_rear_end": gt_object_types[obj.object_id] = "near_miss_rear_end"
                     elif obj.role == "nm_lane_change": gt_object_types[obj.object_id] = "near_miss_lane_change"
                     elif obj.role == "nm_cutoff": gt_object_types[obj.object_id] = "near_miss_cutoff"
                     elif obj.role == "nm_broadside": gt_object_types[obj.object_id] = "near_miss_broadside"
                     elif obj.role == "nm_right_of_way": gt_object_types[obj.object_id] = "near_miss_right_of_way"

        else:
            # Fallback if frames not provided
            gt_object_status = {pid: False for pid in set(p.object_id for p in scenario_pred.predictions)}

        # 2. Determine Prediction per Object
        # We check aggregated max confidence for each object
        pred_object_status = defaultdict(float) # {obj_id: max_confidence}
        pred_intervals = defaultdict(list) # {obj_id: [(t, conf, type)]}
        
        for p in scenario_pred.predictions:
            conf = getattr(p, 'confidence', 0.0)
            if p.is_near_miss and conf == 0.0: conf = 1.0 # Handle binary predictors
            
            if conf > pred_object_status[p.object_id]:
                pred_object_status[p.object_id] = conf
            
            # Store frame-level prediction for TAL (Temporal Action Localization)
            if p.is_near_miss or conf > 0.5:
                 pred_intervals[p.object_id].append((p.timestamp, conf, p.conflict_type.name))
        
        # 3. Object-Level Metrics (Classification)
        obj_tp = 0
        obj_fp = 0
        obj_tn = 0
        obj_fn = 0
        
        # Conflict Type Metrics (Sequence Step D)
        type_correct = 0
        type_total_tp = 0
        type_confusion = [] # (Actual, Predicted)
        
        # Temporal IoU Analysis
        # For each object with GT interval, check overlap
        tiou_scores = []
        metrics_per_object = []  # Detailed metrics per object
        
        brier_sum = 0.0
        
        for obj_id, is_actual_nm in gt_object_status.items():
            pred_conf = pred_object_status.get(obj_id, 0.0)
            is_pred_nm = pred_conf > 0.5 # Threshold
            
            brier_sum += (pred_conf - (1.0 if is_actual_nm else 0.0)) ** 2
            
            # Initialize detail record
            detail = {
                'object_id': obj_id,
                'ground_truth': is_actual_nm,
                'predicted': is_pred_nm,
                'confidence': float(pred_conf),
                'result_type': 'TN', # Default
                'gt_type': 'None',
                'pred_type': 'None',
                'tiou': 0.0,
                'detection_delay': None
            }

            if is_actual_nm:
                # Get GT type
                true_type = gt_object_types.get(obj_id, "unknown")
                detail['gt_type'] = true_type
                
                if is_pred_nm: 
                    obj_tp += 1
                    detail['result_type'] = 'TP'
                    
                    # --- IoU & Conflict Type Check (Only for TPs) ---
                    
                    # 1. Calculate t-IoU
                    # Get GT duration
                    gt_segs = gt_intervals.get(obj_id, [])
                    # Get Pred duration
                    p_frames = sorted([x[0] for x in pred_intervals.get(obj_id, [])])
                    
                    iou = 0.0
                    if gt_segs and p_frames:
                        # Simple overlap of total range for now (Complex multi-segment usually not needed for single event)
                        gt_start, gt_end = gt_segs[0][0], gt_segs[-1][1]
                        gt_dur = max(0.1, gt_end - gt_start)
                        
                        p_start, p_end = p_frames[0], p_frames[-1]
                        p_dur = max(0.1, p_end - p_start)
                        
                        # Intersection
                        i_start = max(gt_start, p_start)
                        i_end = min(gt_end, p_end)
                        intersection = max(0, i_end - i_start)
                        
                        union = gt_dur + p_dur - intersection
                        iou = intersection / union if union > 0 else 0.0
                        
                        # Calculate Detection Delay (First Pred - First GT)
                        # TTA (Time To Accident) is usually (Impact Time - Detection Time)
                        # Here we report latency: how long after "GT Start" did we detect it?
                        delay = p_start - gt_start
                        detail['detection_delay'] = float(delay)
                    
                    detail['tiou'] = float(iou)
                    tiou_scores.append(iou)
                    
                    # 2. Check Conflict Type (Sequence Level)
                    
                    # Get Pred type (Most frequent in sequence)
                    p_types = [x[2] for x in pred_intervals.get(obj_id, []) if x[2] != 'NONE']
                    if not p_types: pred_type = 'NONE'
                    else:
                        from collections import Counter
                        pred_type = Counter(p_types).most_common(1)[0][0]
                    
                    detail['pred_type'] = pred_type
                    
                    # Normalize strings for comparison
                    # GT: 'near_miss_rear_end' -> Pred: 'NEAR_MISS_REAR_END' (usually enum name)
                    
                    # Map Pred Enum names to GT string format or vice versa
                    # Our GT is snake_case 'near_miss_rear_end'
                    # Our Pred matches ConflictType.name (e.g. REAR_END, NEAR_MISS_REAR_END?)
                    # Let's verify Pred Enum names. usually REAR_END, CUT_IN etc.
                    
                    # Quick Normalization Map
                    # We assume Pred is like "REAR_END" or "CUT_IN"
                    # We assume GT is like "near_miss_rear_end"
                    
                    norm_pred = pred_type.upper().replace('NEAR_MISS_', '').replace('SAFE_', '')
                    norm_gt = true_type.upper().replace('NEAR_MISS_', '').replace('SAFE_', '')
                    
                    if norm_pred == norm_gt:
                         type_correct += 1
                    
                    type_total_tp += 1
                    type_confusion.append((norm_gt, norm_pred))

                else: 
                    obj_fn += 1
                    detail['result_type'] = 'FN'
            else:
                if is_pred_nm: 
                    obj_fp += 1
                    detail['result_type'] = 'FP'
                    # Determine what type was falsely predicted
                    p_types = [x[2] for x in pred_intervals.get(obj_id, []) if x[2] != 'NONE']
                    if p_types:
                        from collections import Counter
                        detail['pred_type'] = Counter(p_types).most_common(1)[0][0]
                else: 
                    obj_tn += 1
                    detail['result_type'] = 'TN'
            
            # Append detailed metrics
            metrics_per_object.append(detail)
                
        # Scenario Metrics
        total_objs = len(gt_object_status)
        scen_acc = (obj_tp + obj_tn) / total_objs if total_objs > 0 else 0
        scen_prec = obj_tp / (obj_tp + obj_fp) if (obj_tp + obj_fp) > 0 else 0
        scen_rec = obj_tp / (obj_tp + obj_fn) if (obj_tp + obj_fn) > 0 else 0
        scen_brier = brier_sum / total_objs if total_objs > 0 else 0
        
        # Conflict Type Accuracy
        type_acc = type_correct / type_total_tp if type_total_tp > 0 else 0.0
        
        # Mean t-IoU
        mean_iou = sum(tiou_scores) / len(tiou_scores) if tiou_scores else 0.0
        
        # Determine if scenario has actual near-miss (Global)
        has_actual_near_miss = any(gt_object_status.values())
        
        # Determine if prediction detected near-miss (Global) 
        prediction_detected = any(c > 0.5 for c in pred_object_status.values())
        
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
        
        # Calculate Scenario-Level Confidence
        # Max confidence of any warning in this scenario
        max_confidence = max(pred_object_status.values()) if pred_object_status else 0.0

        # Collect prediction statistics
        all_ttc = [p.ttc for p in scenario_pred.predictions if p.ttc is not None]
        all_drac = [p.drac for p in scenario_pred.predictions if p.drac is not None]
        
        # Collect Conflict Types (Per Object)
        # For each object, find the most severe or most frequent conflict type
        # We focus on objects that were predicted as near-misses or warnings
        obj_conflict_map = defaultdict(list)
        for p in scenario_pred.predictions:
            if p.conflict_type.name != 'NONE' and (p.is_near_miss or p.risk_level.value >= RiskLevel.WARNING.value):
                obj_conflict_map[p.object_id].append(p.conflict_type.name)
        
        # Determine primary conflict type per object
        primary_conflicts = {}
        for oid, ctypes in obj_conflict_map.items():
            if ctypes:
                # Find most frequent
                from collections import Counter
                most_common = Counter(ctypes).most_common(1)[0][0]
                primary_conflicts[oid] = most_common
        
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
            'max_drac': max(all_drac) if all_drac else None,
            'max_confidence': max_confidence,
            'obj_counts': {
                'tp': obj_tp, 'fp': obj_fp, 'tn': obj_tn, 'fn': obj_fn, 'total': total_objs
            },
            'obj_metrics': {
                'accuracy': scen_acc,
                'precision': scen_prec,
                'recall': scen_rec,
                'brier_score': scen_brier,
                'type_accuracy': type_acc, # New
                'mean_tiou': mean_iou      # New
            },
            'type_confusion_entries': type_confusion, # List of (Actual, Pred)
            'tiou_scores_list': tiou_scores,          # Raw scores list for global aggregation
            'predicted_conflict_types': primary_conflicts,  # {obj_id: conflict_type_str}
            'object_details': metrics_per_object     # Detailed object metrics
        }
    
    def evaluate_dataset(self, predictions: Dict[int, ScenarioPrediction],
                        dataset: Dict[int, List[FrameData]],
                        algorithm_name: str = "Unknown") -> EvaluationResults:
        """Evaluate predictions against entire dataset.
        
        Args:
            predictions: Dictionary mapping scenario_id to ScenarioPrediction
            dataset: Dictionary mapping scenario_id to frames (for ground truth)
            algorithm_name: Name of the algorithm used
            
        Returns:
            EvaluationResults
        """
        results = EvaluationResults()
        results.algorithm_name = algorithm_name
        
        # Extract ground truth
        ground_truth = self.extract_ground_truth(dataset)
        
        # Initialize counters
        cm = ConfusionMatrix()
        detection_times = []
        all_ttc = []
        all_drac = []
        risk_counts = defaultdict(int)
        conflict_counts = defaultdict(int)
        
        # Global Aggregates for Sequence Metrics
        global_tiou_scores = []
        global_type_correct = 0
        global_type_total = 0
        
        # Evaluate each scenario
        for scenario_id, scenario_pred in predictions.items():
            gt_events = ground_truth.get(scenario_id, [])
            frames = dataset.get(scenario_id, []) # PASS FRAMES
            
            scenario_result = self.evaluate_scenario(scenario_pred, gt_events, frames)
            results.scenario_results[scenario_id] = scenario_result
            
            # Update GLOBAL Confusion Matrix with OBJECT-LEVEL Counts
            # User Request: Global metrics should reflect object-level performance, not just scenario-level.
            if 'obj_counts' in scenario_result:
                counts = scenario_result['obj_counts']
                cm.true_positives += counts.get('tp', 0)
                cm.true_negatives += counts.get('tn', 0)
                cm.false_positives += counts.get('fp', 0)
                cm.false_negatives += counts.get('fn', 0)
            else:
                # Fallback to Scenario-Level if object counts missing (should not happen with new logic)
                if scenario_result['result_type'] == 'true_positive': cm.true_positives += 1
                elif scenario_result['result_type'] == 'true_negative': cm.true_negatives += 1
                elif scenario_result['result_type'] == 'false_positive': cm.false_positives += 1
                else: cm.false_negatives += 1
            
            # Update Sequence Metrics
            tious = scenario_result.get('tiou_scores_list', [])
            if tious: global_tiou_scores.extend(tious)
            
            t_entries = scenario_result.get('type_confusion_entries', [])
            for act, pred in t_entries:
                if act not in results.type_confusion_matrix: results.type_confusion_matrix[act] = {}
                results.type_confusion_matrix[act][pred] = results.type_confusion_matrix[act].get(pred, 0) + 1
                if act == pred: global_type_correct += 1
                global_type_total += 1

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
        
        if global_tiou_scores:
            results.mean_tiou = float(np.mean(global_tiou_scores))
        if global_type_total > 0:
            results.type_accuracy_global = float(global_type_correct / global_type_total)
        
        # --- PROBABILISTIC METRICS (OBJECT-LEVEL) ---
        # Brier Score = (1/N) * sum((prob - output)^2)
        # AUROC Calculation using Object-Level confidences
        
        brier_sum = 0.0
        y_true = []
        y_scores = []
        total_objects = 0
        
        for s_id, res in results.scenario_results.items():
            if 'object_details' in res:
                # Use Object-Level Data
                for obj in res['object_details']:
                    actual = 1.0 if obj.get('ground_truth', False) else 0.0
                    conf = obj.get('confidence', 0.0)
                    
                    brier_sum += (actual - conf) ** 2
                    y_true.append(actual)
                    y_scores.append(conf)
                    total_objects += 1
            else:
                # Fallback to Scenario-Level Data
                actual = 1.0 if res['has_actual_near_miss'] else 0.0
                predicted_prob = res.get('max_confidence', 0.0)
                if predicted_prob is None: predicted_prob = 0.0
                
                brier_sum += (predicted_prob - actual) ** 2
                y_true.append(actual)
                y_scores.append(predicted_prob)
                total_objects += 1
            
        if total_objects > 0:
            results.brier_score = brier_sum / total_objects
        
        # Calculate AUROC manually (Trapezoidal rule)
        if y_true and y_scores:
            try:
                # simple sort
                combined = list(zip(y_true, y_scores))
                combined.sort(key=lambda x: x[1], reverse=True) # Sort by score desc
                
                n_pos = sum(y_true)
                n_neg = len(y_true) - n_pos
                
                if n_pos > 0 and n_neg > 0:
                    tp = 0
                    fp = 0
                    prev_fpr = 0
                    prev_tpr = 0
                    auroc = 0.0
                    
                    for i in range(len(combined)):
                        if combined[i][0] == 1.0:
                            tp += 1
                        else:
                            fp += 1
                            
                        tpr = tp / n_pos
                        fpr = fp / n_neg
                        
                        # Trapezoid add
                        auroc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2
                        
                        prev_fpr = fpr
                        prev_tpr = tpr
                        
                    results.auroc = auroc
                else:
                    results.auroc = 0.5 # Undefined usually
            except Exception:
                results.auroc = 0.0

        if detection_times:
            results.mean_detection_time = np.mean(detection_times)
            results.std_detection_time = np.std(detection_times)
        
        results.risk_distribution = dict(risk_counts)
        results.conflict_distribution = dict(conflict_counts)
        
        if all_ttc:
            # Filter finite values for mean/std calculations to avoid NaN/Inf warnings
            clean_ttc = [x for x in all_ttc if np.isfinite(x)]
            results.ttc_stats = {
                'min': float(np.min(all_ttc)),
                'max': float(np.max(all_ttc)),
                'mean': float(np.mean(clean_ttc)) if clean_ttc else 0.0,
                'std': float(np.std(clean_ttc)) if clean_ttc else 0.0
            }
        
        if all_drac:
            # Filter finite values for mean/std calculations to avoid NaN/Inf warnings
            clean_drac = [x for x in all_drac if np.isfinite(x)]
            results.drac_stats = {
                'min': float(np.min(all_drac)),
                'max': float(np.max(all_drac)),
                'mean': float(np.mean(clean_drac)) if clean_drac else 0.0,
                'std': float(np.std(clean_drac)) if clean_drac else 0.0
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
        lines.append("NEAR-MISS PREDICTION EVALUATION REPORT (DETAILED ANALYSIS)")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # GLOBAL METRICS SUMMARY
        lines.append("GLOBAL PERFORMANCE METRICS (OBJECT-LEVEL AGGREGATION)")
        lines.append("============================================================")
        lines.append(f"Algorithm:           {results.algorithm_name}")
        cm = results.confusion_matrix
        lines.append(f"Total Scenarios:     {results.total_scenarios}")
        
        # Calculate Object Totals for context
        total_objects = cm.total
        lines.append(f"Total Objects:       {total_objects}")
        lines.append(f"Accuracy:            {cm.accuracy:.4f}")
        lines.append(f"Precision:           {cm.precision:.4f}")
        lines.append(f"Recall:              {cm.recall:.4f}")
        lines.append(f"F1 Score:            {cm.f1_score:.4f}")
        lines.append(f"Brier Score:         {results.brier_score:.4f}")
        lines.append(f"AUROC:               {results.auroc:.4f}")
        lines.append("")
        
        lines.append("SEQUENCE-LEVEL METRICS (GOLD STANDARD)")
        lines.append(f"Conflict Type Acc:   {results.type_accuracy_global:.4f} (on Correct Detections)")
        lines.append(f"Mean t-IoU:          {results.mean_tiou:.4f} (Temporal Overlap Quality)")
        
        if results.type_confusion_matrix:
            lines.append("")
            lines.append("CONFLICT TYPE CONFUSION (Actual -> Predicted):")
            for act, preds in results.type_confusion_matrix.items():
                pred_str = ", ".join([f"{k}:{v}" for k, v in preds.items()])
                lines.append(f"  {act:<20} -> {pred_str}")
                
        lines.append("")
        
        # Per Scenario Report (DETAILED FIRST, then Summary as requested)
        lines.append("DETAILED SCENARIO ANALYSIS")
        lines.append("============================================================")
        
        # Sort by scenario ID
        sorted_scenarios = sorted(results.scenario_results.values(), key=lambda x: x['scenario_id'])
        
        for res in sorted_scenarios:
            s_id = res['scenario_id']['scenario_id'] if isinstance(res['scenario_id'], dict) else res['scenario_id']
            lines.append(f"\n>> SCENARIO {s_id}")
            
            # Object Level Details
            if 'object_details' in res:
                 lines.append(f"   [Object-by-Object Breakdown]")
                 lines.append(f"   {'OID':<4} | {'Status':<6} | {'GT Type':<20} | {'Pred Type':<20} | {'Conf':<6} | {'t-IoU':<6} | {'Delay':<6}")
                 lines.append(f"   {'-'*4: <4} | {'-'*6: <6} | {'-'*20: <20} | {'-'*20: <20} | {'-'*6: <6} | {'-'*6: <6} | {'-'*6: <6}")
                 
                 for obj in res['object_details']:
                     oid = str(obj['object_id'])
                     status = obj.get('result_type', 'UNK')
                     
                     # Format Type Strings
                     if obj.get('gt_type'):
                         gt_t = str(obj.get('gt_type', 'None')).replace('near_miss_', '').upper()
                         if len(gt_t) > 19: gt_t = gt_t[:17] + ".."
                     else:
                         gt_t = "NONE"
                         
                     if obj.get('pred_type'):
                         pred_t = str(obj.get('pred_type', 'None')).replace('NEAR_MISS_', '').replace('SAFE_', '').upper()
                         if len(pred_t) > 19: pred_t = pred_t[:17] + ".."
                     else:
                         pred_t = "NONE"
                     
                     conf = f"{obj.get('confidence', 0.0):.2f}"
                     tiou = f"{obj.get('tiou', 0.0):.2f}"
                     
                     delay_val = obj.get('detection_delay')
                     delay = f"{delay_val:.2f}s" if delay_val is not None else "-"
                     
                     lines.append(f"   {oid:<4} | {status:<6} | {gt_t:<20} | {pred_t:<20} | {conf:<6} | {tiou:<6} | {delay:<6}")
                 
                 lines.append("")
                 
            # Object Level Details (Counts)
            if 'obj_counts' in res and 'obj_metrics' in res:
                 counts = res['obj_counts']
                 metrics = res['obj_metrics']
                 lines.append("   [Object Evaluation]")
                 lines.append(f"   Counts:       TP={counts['tp']} | FP={counts['fp']} | TN={counts['tn']} | FN={counts['fn']} (Total: {counts['total']})")
                 lines.append(f"   Metrics:      Acc={metrics['accuracy']:.2f} | Prec={metrics['precision']:.2f} | Rec={metrics['recall']:.2f} | Brier={metrics['brier_score']:.4f}")
                 lines.append("")

            lines.append(f"   [Scenario Evaluation]")
            lines.append(f"   Status:       {'Correct' if res['result_type'] in ['true_positive', 'true_negative'] else 'Incorrect'} ({res['result_type'].upper()})")
            lines.append(f"   Ground Truth: {'NEAR MISS' if res['has_actual_near_miss'] else 'SAFE'}")
            lines.append(f"   Prediction:   {'NEAR MISS' if res['prediction_detected'] else 'SAFE'} (Confidence: {res.get('max_confidence', 0.0):.4f})")
            lines.append(f"   Max Risk:     {res['max_risk_level']}")
            
            # Display Conflict Types if any
            if 'predicted_conflict_types' in res and res['predicted_conflict_types']:
                conflicts = []
                for oid, ctype in res['predicted_conflict_types'].items():
                    conflicts.append(f"Obj {oid}: {ctype}")
                lines.append(f"   Conflicts:    {', '.join(conflicts)}")
            
            det = f"{res['detection_time']:.2f}s" if res['detection_time'] is not None else "N/A"
            lines.append(f"   Detection T:  {det}")
            
            ttc_val = res.get('min_ttc')
            ttc_str = f"{ttc_val:.2f}s" if ttc_val is not None else "N/A"
            lines.append(f"   Min TTC:      {ttc_str}")
            
            lines.append("-" * 40)

        # Summary Table at the end
        lines.append("\nSUMMARY TABLE")
        lines.append("-" * 95)
        lines.append(f"{'ID':<5} {'Result':<15} {'Actual':<10} {'Pred':<10} {'Risk':<15} {'Min TTC':<10} {'Max DRAC':<10} {'Det.Time':<10}")
        lines.append("-" * 95)
        
        for res in sorted_scenarios:
            s_id = str(res['scenario_id'])
            
            # Result type formatting
            res_type = res['result_type'].replace('_', ' ').title()
            if res_type == "True Positive":
                res_type = "TP"
            elif res_type == "True Negative":
                res_type = "TN"
            elif res_type == "False Positive":
                res_type = "FP"
            elif res_type == "False Negative":
                res_type = "FN"
            elif res_type == "False Negative":
                res_type = "FN"
            
            # Actual and Pred
            actual = "YES" if res['has_actual_near_miss'] else "NO"
            pred = "YES" if res['prediction_detected'] else "NO"
            
            # Risk
            risk = res['max_risk_level']
            
            # TTC
            ttc_val = res.get('min_ttc')
            if ttc_val == float('inf'):
                ttc = "inf"
            elif ttc_val is not None:
                ttc = f"{ttc_val:.2f}"
            else:
                ttc = "-"
            
            # DRAC
            drac_val = res.get('max_drac')
            if drac_val == float('inf'):
                drac = "inf"
            elif drac_val is not None:
                drac = f"{drac_val:.2f}"
            else:
                drac = "-"

            # Detection Time
            det_time = f"{res['detection_time']:.2f}s" if res['detection_time'] is not None else "-"
            
            lines.append(f"{s_id:<5} {res_type:<15} {actual:<10} {pred:<10} {risk:<15} {ttc:<10} {drac:<10} {det_time:<10}")

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
