"""
Stochastic Near-Miss Predictor (Monte Carlo SSM Fusion).

Implements the novel "Stochastic Monte Carlo SSM Fusion" approach defined in gap_analysis_and_novelty.md.
Instead of a single deterministic prediction, this algorithm uses Monte Carlo sampling to generate
an ensemble of possible future trajectories, calculates SSMs for each, and derives a
Probability of Near-Miss (PoNM).
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Sources.scenario_types import TrackedObject, EgoVehicle, FrameData
from Utils.config import SimulationConfig, SSMThresholds, RiskLevel, DEFAULT_SIMULATION_CONFIG
from .base_algorithm import NearMissAlgorithm, ScenarioPrediction
from .near_miss_predictor import PredictionResult, ConflictType
from .ssm_calculator import SSMCalculator, SSMResult
from .registry import AlgorithmRegistry


@AlgorithmRegistry.register
class StochasticPredictor(NearMissAlgorithm):
    """
    Probabilistic predictor using Monte Carlo sampling of object trajectories.
    """

    @classmethod
    def get_name(cls) -> str:
        return "Stochastic (Monte Carlo)"

    @property
    def name(self) -> str:
        return "Stochastic (Monte Carlo)"
    
    def __init__(self, config: SimulationConfig = None, thresholds: SSMThresholds = None):
        super().__init__(config)
        self.config = config or DEFAULT_SIMULATION_CONFIG
        self.thresholds = thresholds or SSMThresholds()
        self.ssm_calculator = SSMCalculator(self.thresholds)
        
        # Monte Carlo Parameters
        self.num_samples = 30  # Number of particles/samples per object
        self.prediction_depth = 1 # We use instantaneous state perturbation mostly, or simple lookahead
        
        # Uncertainty Parameters (matches DataGenerato noise roughly, usually estimated by Kalman Filter)
        self.pos_uncertainty_std = 0.5  # meters
        self.vel_uncertainty_std = 1.0  # m/s
        self.acc_uncertainty_std = 2.0 # m/s^2 (Process noise)

        self.rng = np.random.default_rng()

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
        # abs(dy) < 2.0 * LW = 7 m explicitly excludes far-lateral side-road objects.
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

    def run_prediction(self, dataset: Dict[int, List[FrameData]]) -> Dict[int, ScenarioPrediction]:
        """Run prediction on the entire dataset."""
        results = {}
        for scenario_id, frames in dataset.items():
            results[scenario_id] = self.predict_scenario(scenario_id, frames)
        return results

    def predict_scenario(self, scenario_id: int, frames: List[FrameData]) -> ScenarioPrediction:
        """Run prediction on a single scenario using Monte Carlo method."""
        predictions = []
        near_miss_detected = False
        first_detection_time = None
        max_risk = RiskLevel.SAFE
        
        # Running statistics
        total_near_miss_frames = 0
        max_confidence = 0.0
        
        for frame in frames:
            frame_preds = []
            
            for obj in frame.objects:
                # Run Monte Carlo Prediction for this object
                mc_result = self.predict_single_object_stochastic(frame, obj)
                
                frame_preds.append(mc_result)
                
                # Check metrics
                if hasattr(mc_result, 'confidence'):
                    if mc_result.confidence > max_confidence:
                        max_confidence = mc_result.confidence

                if mc_result.is_near_miss:
                    near_miss_detected = True
                    total_near_miss_frames += 1
                    if first_detection_time is None:
                        first_detection_time = frame.timestamp
                    
                    if mc_result.risk_level.value > max_risk.value:
                        max_risk = mc_result.risk_level
            
            predictions.extend(frame_preds)
            
        return ScenarioPrediction(
            scenario_id=scenario_id,
            predictions=predictions,
            near_miss_detected=near_miss_detected,
            first_detection_time=first_detection_time,
            max_risk_level=max_risk,
            max_confidence=max_confidence,
            summary={
                'total_frames': len(frames),
                'total_near_misses': total_near_miss_frames
            }
        )

    def predict_single_object_stochastic(self, frame: FrameData, obj: TrackedObject) -> PredictionResult:
        """
        Perform Monte Carlo sampling to calculate Probability of Near Miss (PoNM).
        """
        ego = frame.ego
        
        # 1. Deterministic Calculation (Center of distribution)
        # We assume the object state provided is the mean (x, y, vx, vy)
        
        # 2. Monte Carlo Sampling
        # Generate N perturbed versions of the object
        
        unsafe_samples = 0
        collision_samples = 0
        
        # We will collect 'samples' of SSM values to compute statistics
        ttc_samples = []
        drac_samples = []
        
        for _ in range(self.num_samples):
            # Sample State
            sample_obj = self._sample_object_state(obj)
            
            # Predict Collision likelihood for this sample
            # We use the SSM Calculator on this perturbed state
            ssm_res = self.ssm_calculator.calculate_all_ssm(ego, sample_obj)
            
            # Use deterministic thresholds on this sample to classify it
            is_sample_unsafe = False
            
            # Check TTC Criteria
            if ssm_res.ttc is not None:
                ttc_samples.append(ssm_res.ttc)
                if ssm_res.ttc < self.thresholds.ttc_near_miss:
                    is_sample_unsafe = True
                if ssm_res.ttc < 0.5: # Critical collision threshold
                    collision_samples += 1
            
            # Check DRAC Criteria
            if ssm_res.drac is not None:
                drac_samples.append(ssm_res.drac)
                if ssm_res.drac > self.thresholds.drac_near_miss:
                    is_sample_unsafe = True
            
            if is_sample_unsafe:
                unsafe_samples += 1
                
        # 3. Aggregate Probabilities
        prob_near_miss = unsafe_samples / self.num_samples
        prob_collision = collision_samples / self.num_samples
        
        # 4. Determine Classification (Risk > 0.4?? Or keep it granular?)
        # For the binary classification ('is_near_miss' field), we still need a threshold on the probability.
        # But prediction.confidence will store the probability itself.
        
        PROBABILITY_THRESHOLD = 0.4 # Significance threshold
        
        is_near_miss = prob_near_miss > PROBABILITY_THRESHOLD
        
        # 5. Compute Expected SSM values (Mean of samples)
        expected_ttc = float(np.mean(ttc_samples)) if ttc_samples else None
        expected_drac = float(np.mean(drac_samples)) if drac_samples else None
        
        # Risk Level based on Probability
        risk_level = RiskLevel.SAFE
        if prob_near_miss > 0.8:
            risk_level = RiskLevel.COLLISION # High confidence risk
        elif prob_near_miss > 0.4:
            risk_level = RiskLevel.NEAR_MISS
        elif prob_near_miss > 0.1:
            risk_level = RiskLevel.WARNING
            
        warning_msg = f"PoNM: {prob_near_miss:.2f}" if prob_near_miss > 0.1 else ""
        
        # Detect conflict type on the mean state
        conflict_type = self.detect_conflict_type(ego, obj)
        
        # Calculate base distance and velocity for display
        base_dist = np.sqrt(obj.x**2 + obj.y**2)
        rel_vel = np.sqrt(obj.vx**2 + obj.vy**2) # Approximate relative speed (assuming ego is reference frame origin/static in relative terms provided by track?) 
        # Actually tracked object coordinates are usually relative to ego.
        
        # We return a standard PredictionResult, but 'confidence' is now the calibrated probability
        return PredictionResult(
            frame_id=frame.frame_id,
            timestamp=frame.timestamp,
            object_id=obj.object_id,
            object_class=obj.object_class,
            distance=base_dist, 
            relative_velocity=rel_vel,
            ttc=expected_ttc,
            drac=expected_drac,
            mdr=None,
            risk_level=risk_level,
            conflict_type=conflict_type, 
            collision_predicted=prob_collision > 0.5,
            time_to_event=expected_ttc,
            confidence=prob_near_miss, # <--- KEY NOVELTY: Using Probability as Confidence
            is_near_miss=is_near_miss,
            warning_message=warning_msg
        )

    def _sample_object_state(self, obj: TrackedObject) -> TrackedObject:
        """Create a randomized copy of the track object."""
        # Perturb Position
        nx = obj.x + self.rng.normal(0, self.pos_uncertainty_std)
        ny = obj.y + self.rng.normal(0, self.pos_uncertainty_std)
        
        # Perturb Velocity
        nvx = obj.vx + self.rng.normal(0, self.vel_uncertainty_std)
        nvy = obj.vy + self.rng.normal(0, self.vel_uncertainty_std)
        
        # Return new object (shallow copy structure, new values)
        # Note: TrackedObject is a dataclass, so easy to construct
        return TrackedObject(
            object_id=obj.object_id,
            x=nx,
            y=ny,
            vx=nvx,
            vy=nvy,
            length=obj.length,
            width=obj.width,
            object_class=obj.object_class,
            heading=obj.heading,
            role=obj.role
        )
