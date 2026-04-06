"""
Naive Distance-Based Predictor for Baseline Comparison.
"""

from .base_algorithm import NearMissAlgorithm, ScenarioPrediction
from .near_miss_predictor import PredictionResult, ConflictType
from .registry import AlgorithmRegistry
from Utils.config import RiskLevel, SimulationConfig

@AlgorithmRegistry.register
class DistancePredictor(NearMissAlgorithm):
    """
    A naive baseline algorithm that predicts a near-miss solely based on 
    Euclidean distance, ignoring velocity and trajectory.
    """

    @classmethod
    def get_name(cls) -> str:
        return "Baseline (Distance Only)"

    @property
    def name(self) -> str:
        return "Baseline (Distance Only)"
    
    def __init__(self, config: SimulationConfig = None):
        super().__init__(config)
        # Naive threshold: If closer than 8 meters, it's a near-miss
        self.DISTANCE_THRESHOLD = 8.0 
        
    def run_prediction(self, dataset) -> ScenarioPrediction:
        """Run prediction on a single scenario."""
        # This wrapper handles the full dictionary, but base class usually expects scenario-by-scenario
        # For simplicity in this architecture, we follow the pattern of the main predictor
        pass

    def predict_scenario(self, scenario_id: int, frames: list) -> ScenarioPrediction:
        predictions = []
        near_miss_detected = False
        first_detection_time = None
        max_risk = RiskLevel.SAFE
        
        for frame_idx, frame in enumerate(frames):
            for obj in frame.objects:
                # Calculate simple Euclidean distance
                dist = (obj.x**2 + obj.y**2)**0.5
                
                is_risk = dist < self.DISTANCE_THRESHOLD
                
                risk_level = RiskLevel.NEAR_MISS if is_risk else RiskLevel.SAFE
                
                if is_risk:
                    near_miss_detected = True
                    max_risk = RiskLevel.NEAR_MISS
                    if first_detection_time is None:
                        first_detection_time = frame.timestamp
                
                # Create result object matches the interface
                res = PredictionResult(
                    frame_id=frame.frame_id,
                    timestamp=frame.timestamp,
                    object_id=obj.object_id,
                    object_class=obj.object_class,
                    distance=dist,
                    relative_velocity=0.0, # Naive model ignores this
                    ttc=None,
                    drac=None,
                    mdr=None,
                    risk_level=risk_level,
                    conflict_type=ConflictType.NONE,
                    collision_predicted=False,
                    time_to_event=None,
                    confidence=1.0 if is_risk else 0.0,
                    is_near_miss=is_risk,
                    warning_message="Basic proximity warning" if is_risk else ""
                )
                predictions.append(res)
                
        return ScenarioPrediction(
            scenario_id=scenario_id,
            predictions=predictions,
            near_miss_detected=near_miss_detected,
            first_detection_time=first_detection_time,
            max_risk_level=max_risk,
            summary={'total_frames': len(frames)}
        )
