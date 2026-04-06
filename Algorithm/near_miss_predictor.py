"""
Deterministic Near-Miss Predictor.

Implements rule-based near-miss prediction using multiple SSMs and trajectory prediction.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Sources.scenario_types import TrackedObject, EgoVehicle, FrameData
from Utils.config import SSMThresholds, RiskLevel, SimulationConfig, DEFAULT_SIMULATION_CONFIG
from .ssm_calculator import SSMCalculator, SSMResult
from .trajectory_model import TrajectoryPredictor, ConstantVelocityModel
from .base_algorithm import NearMissAlgorithm, ScenarioPrediction
from .registry import AlgorithmRegistry


class ConflictType(Enum):
    """Types of traffic conflicts."""
    NONE = "none"
    REAR_END = "rear_end"        # Following vehicle forced to stop suddenly
    LANE_CHANGE = "lane_change"  # Slow moving car changes lanes -> fast car slows/swerves
    CUTOFF = "cutoff"            # Turning movement across path -> alter motion
    BROADSIDE = "broadside"      # Passing into intersection -> blocked path
    RIGHT_OF_WAY = "right_of_way" # Two drivers -> same point -> refused to grant path


@dataclass
class PredictionResult:
    """Result of near-miss prediction for a single object."""
    frame_id: int
    timestamp: float
    object_id: int
    object_class: str
    
    # Current state
    distance: float
    relative_velocity: float
    
    # SSM values
    ttc: Optional[float]
    drac: Optional[float]
    mdr: Optional[float]
    
    # Prediction
    risk_level: RiskLevel
    conflict_type: ConflictType
    collision_predicted: bool
    time_to_event: Optional[float]
    confidence: float
    
    # Additional info
    is_near_miss: bool = False
    warning_message: str = ""



@AlgorithmRegistry.register
class NearMissPredictor(NearMissAlgorithm):
    """Deterministic near-miss predictor using SSMs and rule-based classification."""

    @classmethod
    def get_name(cls) -> str:
        return "Rule-Based SSM"

    @property
    def name(self) -> str:
        return "Rule-Based SSM"
    
    def __init__(self, config: SimulationConfig = None, thresholds: SSMThresholds = None):
        super().__init__(config)
        self.config = config or DEFAULT_SIMULATION_CONFIG
        self.thresholds = thresholds or SSMThresholds()
        
        self.ssm_calculator = SSMCalculator(self.thresholds)
        self.trajectory_predictor = TrajectoryPredictor(self.config.dt)
        
        # Object tracking history for each object_id
        self.object_histories: Dict[int, List[TrackedObject]] = {}
        self.max_history_length = 30  # frames
        
        # Near-miss classification parameters
        self.near_miss_ttc_threshold = self.thresholds.ttc_near_miss
        self.near_miss_drac_threshold = self.thresholds.drac_near_miss
        self.near_miss_mdr_threshold = self.thresholds.mdr_near_miss
        
    def update_history(self, frame: FrameData):
        """Update object tracking histories."""
        for obj in frame.objects:
            if obj.object_id not in self.object_histories:
                self.object_histories[obj.object_id] = []
            
            self.object_histories[obj.object_id].append(obj)
            
            # Limit history length
            if len(self.object_histories[obj.object_id]) > self.max_history_length:
                self.object_histories[obj.object_id].pop(0)
    
    def clear_history(self):
        """Clear all tracking histories."""
        self.object_histories = {}
    
    def detect_conflict_type(self, ego: EgoVehicle, obj: TrackedObject) -> ConflictType:
        """Detect the type of potential conflict.
        
        Mapped to 5 specific types:
        1. Rear-end: Following vehicle forced to stop suddenly (braking).
        2. Lane-change: Slow moving car changes lanes -> fast car slows/swerves.
        3. Cutoff: Turning movement across path -> alter motion.
        4. Broadside: Passing into intersection -> blocked path of cross traffic.
        5. Right-of-way: Two drivers proceeded to same point -> refused to grant clear path.
        """
        # Relative position and velocity
        dx = obj.x
        dy = obj.y
        vx = obj.vx
        vy = obj.vy
        
        # Spatial zones
        ahead = dx > 0
        behind = dx < 0
        LW = self.config.lane_width          # 3.5 m standard
        same_lane = abs(dy) < LW / 2
        adjacent_lane = LW / 2 <= abs(dy) < 1.5 * LW

        # Each condition uses an exclusive geometric signature.
        # Key design notes:
        #   - In the ego-centric frame, objects stationary in world-X have vx ≈ -ego_velocity
        #     (~-14 m/s), so abs(vx) is NOT a reliable crossing discriminator.
        #   - Lateral offset (abs(dy)) separates side-road conflict types from lane-adjacent ones.

        # 1. Broadside (HIGHEST PRIORITY)
        # Signature: very high lateral speed (cross traffic), object not in same lane,
        # within the forward intersection zone. abs(vx) is NOT gated: crossing objects
        # in ego-centric frame always have |vx| ≈ ego_velocity regardless of crossing speed.
        # Threshold 4.0 m/s filters stochastic noise peaks from CUTOFF/REAR_END objects
        # (which have peak |vy| ≈ 1.75 m/s; real cross traffic has |vy| = 6-10 m/s).
        if abs(vy) > 4.0 and not same_lane and -10 < dx < 45:
            return ConflictType.BROADSIDE

        # 2. Right-of-way
        # Signature: lateral convergence from a far side position (side road / intersection arm).
        # abs(dy) > 1.5*LW (5.25 m) only captures objects beyond the adjacent-lane zone
        # (LANE_CHANGE/CUTOFF have |dy| ≈ LW = 3.5 m), preventing false noise-driven matches.
        if 0 < dx < 60 and abs(dy) > 1.5 * LW and abs(vy) > 0.3:
            toward_center = (dy > 0 and vy < -0.3) or (dy < 0 and vy > 0.3)
            if toward_center:
                return ConflictType.RIGHT_OF_WAY

        # 3. Cutoff
        # Signature: lateral intrusion from the adjacent-lane zone (not far out).
        # dx extended to 40 m to cover the full near-miss detection window.
        # abs(dy) < 2.0 * LW = 7 m explicitly excludes far-lateral side-road objects
        # (ROW / BROADSIDE), which is the main fix for RIGHT_OF_WAY → CUTOFF confusion.
        if 0 < dx < 40 and 0 < abs(dy) < 2.0 * LW and not same_lane:
            toward_center = (dy > 0 and vy < -0.5) or (dy < 0 and vy > 0.5)
            if toward_center:
                return ConflictType.CUTOFF

        # 4. Lane-change
        # Signature: adjacent lane, lateral drift toward ego, significant speed differential.
        # Cap raised to |vy| < 2.5 to match actual peak lane-change lateral velocity
        # (~1.75 m/s = 1.0 * lane_width / maneuver_duration * 1.5).
        # vx < -3.0 requires a strong speed differential to avoid REAR_END noise confusion.
        if adjacent_lane and abs(vy) < 2.5:
            toward_ego = (dy > 0 and vy < -0.2) or (dy < 0 and vy > 0.2)
            if toward_ego and vx < -3.0:
                return ConflictType.LANE_CHANGE

        # 5. Rear-end (LOWEST PRIORITY)
        # Signature: purely longitudinal closing, same lane, negligible lateral motion.
        if ahead and same_lane and abs(vy) < 1.0 and vx < -1.0:
            return ConflictType.REAR_END

        return ConflictType.NONE
    
    def predict_single_object(self, frame: FrameData, obj: TrackedObject) -> PredictionResult:
        """Make near-miss prediction for a single object.
        
        Args:
            frame: Current frame data
            obj: Object to analyze
            
        Returns:
            PredictionResult
        """
        ego = frame.ego
        
        # Calculate SSM
        ssm_result = self.ssm_calculator.calculate_all_ssm(ego, obj)
        
        # Detect conflict type
        conflict_type = self.detect_conflict_type(ego, obj)
        
        # Get object history
        obj_history = self.object_histories.get(obj.object_id, [])
        
        # Predict trajectory
        predicted_collision = None
        if conflict_type != ConflictType.NONE:
            predicted_collision = self.trajectory_predictor.predict_collision_point(
                ego, obj, self.config.prediction_horizon
            )
        
        # Determine collision prediction
        collision_predicted = predicted_collision is not None
        time_to_event = predicted_collision[2] if predicted_collision else ssm_result.ttc
        
        # Calculate confidence based on consistency
        confidence = self._calculate_confidence(ssm_result, obj_history, conflict_type)
        
        # Classify as near-miss
        is_near_miss = self._classify_near_miss(ssm_result, conflict_type, time_to_event)
        
        # Generate warning message
        warning_msg = self._generate_warning(ssm_result, conflict_type, is_near_miss)
        
        return PredictionResult(
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            object_id=obj.object_id,
            object_class=obj.object_class,
            distance=ssm_result.distance or 0,
            relative_velocity=ssm_result.relative_velocity or 0,
            ttc=ssm_result.ttc,
            drac=ssm_result.drac,
            mdr=ssm_result.mdr,
            risk_level=ssm_result.risk_level,
            conflict_type=conflict_type,
            collision_predicted=collision_predicted,
            time_to_event=time_to_event,
            confidence=confidence,
            is_near_miss=is_near_miss,
            warning_message=warning_msg
        )
    
    def _calculate_confidence(self, ssm: SSMResult, history: List[TrackedObject],
                             conflict_type: ConflictType) -> float:
        """Calculate prediction confidence.
        
        Based on:
        - Consistency of SSM over history
        - Multiple SSMs agreeing on risk level
        - Conflict type clarity
        """
        confidence = 0.5  # Base confidence
        
        # More history increases confidence
        if len(history) >= 5:
            confidence += 0.1
        if len(history) >= 15:
            confidence += 0.1
        
        # Multiple SSMs agreeing increases confidence
        risk_indicators = 0
        if ssm.ttc is not None and ssm.ttc < self.thresholds.ttc_warning:
            risk_indicators += 1
        if ssm.drac is not None and ssm.drac > self.thresholds.drac_warning:
            risk_indicators += 1
        if ssm.mdr is not None and ssm.mdr < self.thresholds.mdr_warning:
            risk_indicators += 1
        
        if risk_indicators >= 2:
            confidence += 0.2
        if risk_indicators >= 3:
            confidence += 0.1
        
        # Known conflict type increases confidence
        if conflict_type != ConflictType.NONE:
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _classify_near_miss(self, ssm: SSMResult, conflict_type: ConflictType,
                           time_to_event: Optional[float]) -> bool:
        """Classify whether situation is a near-miss.
        
        Near-miss criteria:
        1. TTC below threshold AND conflict type detected
        2. DRAC above threshold
        3. MDR below threshold
        4. Multiple criteria simultaneously triggered
        """
        # Count triggered criteria
        criteria_met = 0
        
        # TTC criterion
        ttc_critical = ssm.ttc is not None and ssm.ttc < self.near_miss_ttc_threshold
        if ttc_critical:
            criteria_met += 1
        
        # DRAC criterion
        drac_critical = ssm.drac is not None and ssm.drac > self.near_miss_drac_threshold
        if drac_critical:
            criteria_met += 1
        
        # MDR criterion
        mdr_critical = ssm.mdr is not None and ssm.mdr < self.near_miss_mdr_threshold
        if mdr_critical:
            criteria_met += 1
        
        # Classification rules
        if ssm.risk_level in [RiskLevel.NEAR_MISS, RiskLevel.COLLISION]:
            return True
        
        if criteria_met >= 2:
            return True
        
        if criteria_met >= 1 and conflict_type != ConflictType.NONE:
            return True
        
        return False
    
    def _generate_warning(self, ssm: SSMResult, conflict_type: ConflictType,
                         is_near_miss: bool) -> str:
        """Generate human-readable warning message."""
        if not is_near_miss:
            return ""
        
        messages = []
        
        # Conflict type message
        conflict_msgs = {
            ConflictType.REAR_END: "Rear-end collision risk",
            ConflictType.LANE_CHANGE: "Lane change conflict",
            ConflictType.CUTOFF: "Cutoff / Aggressive turn",
            ConflictType.BROADSIDE: "Broadside / Crossing conflict",
            ConflictType.RIGHT_OF_WAY: "Right-of-Way violation"
        }
        
        if conflict_type in conflict_msgs:
            messages.append(conflict_msgs[conflict_type])
        
        # SSM values
        if ssm.ttc is not None:
            messages.append(f"TTC: {ssm.ttc:.1f}s")
        if ssm.drac is not None:
            messages.append(f"DRAC: {ssm.drac:.1f}m/s²")
        
        return " | ".join(messages)
    
    def predict_frame(self, frame: FrameData) -> List[PredictionResult]:
        """Make predictions for all objects in a frame.
        
        Args:
            frame: Frame data
            
        Returns:
            List of PredictionResult
        """
        # Update tracking history
        self.update_history(frame)
        
        # Predict for each object
        results = []
        for obj in frame.objects:
            result = self.predict_single_object(frame, obj)
            results.append(result)
        
        return results
    
    def predict_scenario(self, scenario_id: int, 
                        frames: List[FrameData]) -> ScenarioPrediction:
        """Make predictions for a complete scenario.
        
        Args:
            scenario_id: Scenario identifier
            frames: List of frame data
            
        Returns:
            ScenarioPrediction with all results
        """
        self.clear_history()
        
        all_predictions = []
        near_miss_detected = False
        first_detection_time = None
        max_risk = RiskLevel.SAFE
        
        # Statistics
        total_near_misses = 0
        objects_with_near_miss = set()
        
        for frame in frames:
            frame_predictions = self.predict_frame(frame)
            all_predictions.extend(frame_predictions)
            
            for pred in frame_predictions:
                # Track max risk level
                if pred.risk_level.value > max_risk.value:
                    max_risk = pred.risk_level
                
                # Track near-miss detection
                if pred.is_near_miss:
                    total_near_misses += 1
                    objects_with_near_miss.add(pred.object_id)
                    
                    if not near_miss_detected:
                        near_miss_detected = True
                        first_detection_time = pred.timestamp
        
        # Create summary
        summary = {
            'total_frames': len(frames),
            'total_predictions': len(all_predictions),
            'total_near_misses': total_near_misses,
            'objects_with_near_miss': len(objects_with_near_miss),
            'max_risk_level': max_risk.name,
            'first_detection_time': first_detection_time
        }
        
        return ScenarioPrediction(
            scenario_id=scenario_id,
            predictions=all_predictions,
            near_miss_detected=near_miss_detected,
            first_detection_time=first_detection_time,
            max_risk_level=max_risk,
            summary=summary
        )
    
    def predict_dataset(self, dataset: Dict[int, List[FrameData]]) -> Dict[int, ScenarioPrediction]:
        """Make predictions for entire dataset.
        
        Args:
            dataset: Dictionary mapping scenario_id to frames
            
        Returns:
            Dictionary mapping scenario_id to ScenarioPrediction
        """
        results = {}
        
        for scenario_id, frames in dataset.items():
            prediction = self.predict_scenario(scenario_id, frames)
            results[scenario_id] = prediction
        
        return results
