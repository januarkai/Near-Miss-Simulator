"""
Surrogate Safety Measures (SSM) Calculator.

Implements common traffic safety measures for near-miss detection:
- TTC (Time to Collision)
- DRAC (Deceleration Rate to Avoid Collision)  
- PET (Post-Encroachment Time)
- MDR (Minimum Distance Ratio)
- TIT (Time Integrated TTC)
- TET (Time Exposed TTC)
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Sources.scenario_types import TrackedObject, EgoVehicle, FrameData
from Utils.config import SSMThresholds, RiskLevel


@dataclass
class SSMResult:
    """Results from SSM calculation for a single object."""
    object_id: int
    ttc: Optional[float] = None  # Time to Collision (seconds)
    ttc_inverse: Optional[float] = None  # 1/TTC for integration
    drac: Optional[float] = None  # Deceleration Rate to Avoid Collision (m/s²)
    pet: Optional[float] = None  # Post-Encroachment Time (seconds)
    mdr: Optional[float] = None  # Minimum Distance Ratio
    distance: Optional[float] = None  # Current distance (meters)
    relative_velocity: Optional[float] = None  # Relative approach velocity (m/s)
    collision_point: Optional[Tuple[float, float]] = None  # Predicted collision location
    risk_level: RiskLevel = RiskLevel.SAFE


class SSMCalculator:
    """Calculator for Surrogate Safety Measures."""
    
    def __init__(self, thresholds: SSMThresholds = None):
        self.thresholds = thresholds or SSMThresholds()
        
        # Minimum safe distances
        self.min_longitudinal_gap = 2.0  # meters
        self.min_lateral_gap = 0.5  # meters
        
    def calculate_distance(self, ego: EgoVehicle, obj: TrackedObject) -> Tuple[float, float, float]:
        """Calculate distance between ego and object (centre-to-centre).

        Object size is intentionally excluded: sensor-estimated bounding-box
        dimensions are unreliable, so all distances are measured between
        object centroids and the ego origin.

        Returns:
            Tuple of (euclidean_distance, longitudinal_distance, lateral_distance)
        """
        # Longitudinal distance (centre-to-centre along x-axis)
        long_dist = abs(obj.x)

        # Lateral distance (centre-to-centre along y-axis)
        lat_dist = abs(obj.y)

        # Euclidean distance (centre-to-centre)
        eucl_dist = np.sqrt(obj.x**2 + obj.y**2)

        return eucl_dist, max(0, long_dist), max(0, lat_dist)
    
    def calculate_ttc(self, ego: EgoVehicle, obj: TrackedObject) -> Optional[float]:
        """Calculate Time to Collision (TTC).
        
        TTC is defined as the time remaining until collision if both vehicles
        maintain their current velocities and trajectories.
        
        For longitudinal TTC (rear-end scenario):
        TTC = (x_obj - L_ego/2 - L_obj/2) / (v_ego - v_obj)
        
        Returns:
            TTC in seconds, or None if no collision trajectory
        """
        eucl_dist, long_dist, lat_dist = self.calculate_distance(ego, obj)
        
        # Check if object is ahead and in potential collision path
        if obj.x <= 0:
            return None  # Object behind ego
        
        # Relative velocity (positive means approaching)
        rel_vx = -obj.vx  # In ego frame, negative vx means object is slower (approaching)
        
        # Check if approaching
        if rel_vx <= 0:
            return None  # Not approaching (diverging)
        
        # Check lateral overlap potential (centre-to-centre)
        # Consider collision possible if lateral gap < threshold after accounting for velocities
        future_lat_dist = lat_dist - abs(obj.vy) * (long_dist / rel_vx if rel_vx > 0.1 else 100)

        if future_lat_dist > self.min_lateral_gap:
            return None  # Will pass without lateral overlap
        
        # Calculate TTC
        if rel_vx > 0.01:  # Minimum relative velocity threshold
            ttc = long_dist / rel_vx
            return max(0, ttc)
        
        return None
    
    def calculate_ttc_2d(self, ego: EgoVehicle, obj: TrackedObject, 
                        prediction_horizon: float = 10.0) -> Optional[float]:
        """Calculate 2D TTC considering both longitudinal and lateral motion.
        
        Uses trajectory intersection approach for more accurate TTC.
        """
        # Relative position
        dx = obj.x
        dy = obj.y
        
        # Relative velocity
        dvx = -obj.vx  # In ego frame
        dvy = -obj.vy
        
        # Conflict zone threshold (centre-to-centre; no size correction applied)
        safe_dist = self.min_longitudinal_gap
        
        # Solve for time when distance equals safe_dist
        # |p(t)| = |p0 + v*t| = safe_dist
        # This is a quadratic equation
        
        a = dvx**2 + dvy**2
        b = 2 * (dx * dvx + dy * dvy)
        c = dx**2 + dy**2 - safe_dist**2
        
        if abs(a) < 1e-6:
            # Constant relative position
            return None if c > 0 else 0.0
        
        discriminant = b**2 - 4*a*c
        
        if discriminant < 0:
            return None  # No intersection
        
        sqrt_disc = np.sqrt(discriminant)
        t1 = (-b - sqrt_disc) / (2*a)
        t2 = (-b + sqrt_disc) / (2*a)
        
        # Find smallest positive time
        times = [t for t in [t1, t2] if 0 < t <= prediction_horizon]
        
        if times:
            return min(times)
        
        return None
    
    def calculate_drac(self, ego: EgoVehicle, obj: TrackedObject) -> Optional[float]:
        """Calculate Deceleration Rate to Avoid Collision (DRAC).
        
        DRAC represents the minimum deceleration required by the following vehicle
        to avoid collision with the leading vehicle.
        
        DRAC = (v_rel)² / (2 * distance)
        
        Returns:
            DRAC in m/s², or None if not applicable
        """
        if obj.x <= 0:
            return None  # Object not ahead
        
        _, long_dist, lat_dist = self.calculate_distance(ego, obj)
        
        # Check if in same lane (lateral overlap possible)
        if lat_dist > self.min_lateral_gap:
            return None
        
        # Relative approach velocity
        rel_vx = -obj.vx  # Positive means approaching
        
        if rel_vx <= 0:
            return None  # Not approaching
        
        if long_dist <= 0:
            return float('inf')  # Already overlapping
        
        # Calculate DRAC
        drac = (rel_vx ** 2) / (2 * long_dist)
        
        return drac
    
    def calculate_pet(self, ego_trajectory: List[Tuple[float, float, float]],
                     obj_trajectory: List[Tuple[float, float, float]],
                     spatial_threshold: float = 2.0) -> Optional[float]:
        """Calculate Post-Encroachment Time (PET).
        
        PET is the time difference between two vehicles occupying the same 
        spatial location (conflict point).
        
        Args:
            ego_trajectory: List of (x, y, timestamp) for ego
            obj_trajectory: List of (x, y, timestamp) for object
            spatial_threshold: Distance threshold to consider same location
            
        Returns:
            PET in seconds, or None if no encroachment detected
        """
        min_pet = None
        
        for ego_x, ego_y, ego_t in ego_trajectory:
            for obj_x, obj_y, obj_t in obj_trajectory:
                dist = np.sqrt((ego_x - obj_x)**2 + (ego_y - obj_y)**2)
                
                if dist < spatial_threshold:
                    pet = abs(ego_t - obj_t)
                    if min_pet is None or pet < min_pet:
                        min_pet = pet
        
        return min_pet
    
    def calculate_mdr(self, ego: EgoVehicle, obj: TrackedObject) -> float:
        """Calculate Minimum Distance Ratio (MDR).
        
        MDR = actual_distance / safe_minimum_distance
        
        Safe minimum distance is typically based on speed and reaction time:
        d_safe = v * t_reaction + d_min
        
        Returns:
            MDR (dimensionless, <1 means unsafe)
        """
        eucl_dist, long_dist, lat_dist = self.calculate_distance(ego, obj)
        
        # Reaction time based safe distance
        reaction_time = 1.5  # seconds
        v_ego = ego.vx  # Ego absolute velocity
        
        # Safe distance calculation
        d_safe = v_ego * reaction_time + self.min_longitudinal_gap
        
        # For lateral safety
        if abs(obj.y) < self.min_lateral_gap:
            # Object within lateral threshold - use longitudinal distance
            actual_dist = long_dist
        else:
            # Object offset laterally - use combined distance
            actual_dist = np.sqrt(long_dist**2 + lat_dist**2)
        
        if d_safe <= 0:
            return float('inf')
        
        mdr = actual_dist / d_safe
        return mdr
    
    def classify_risk(self, ssm_result: SSMResult) -> RiskLevel:
        """Classify risk level based on SSM values.
        
        Uses a multi-criteria approach with weighted combination.
        """
        risk_scores = []
        
        # TTC-based risk (lower TTC = higher risk)
        if ssm_result.ttc is not None:
            if ssm_result.ttc < self.thresholds.ttc_collision:
                risk_scores.append(3)
            elif ssm_result.ttc < self.thresholds.ttc_near_miss:
                risk_scores.append(2)
            elif ssm_result.ttc < self.thresholds.ttc_warning:
                risk_scores.append(1)
            else:
                risk_scores.append(0)
        
        # DRAC-based risk (higher DRAC = higher risk)
        if ssm_result.drac is not None:
            if ssm_result.drac > self.thresholds.drac_collision:
                risk_scores.append(3)
            elif ssm_result.drac > self.thresholds.drac_near_miss:
                risk_scores.append(2)
            elif ssm_result.drac > self.thresholds.drac_warning:
                risk_scores.append(1)
            else:
                risk_scores.append(0)
        
        # MDR-based risk (lower MDR = higher risk)
        if ssm_result.mdr is not None:
            if ssm_result.mdr < self.thresholds.mdr_collision:
                risk_scores.append(3)
            elif ssm_result.mdr < self.thresholds.mdr_near_miss:
                risk_scores.append(2)
            elif ssm_result.mdr < self.thresholds.mdr_warning:
                risk_scores.append(1)
            else:
                risk_scores.append(0)
        
        # Combined risk level (take maximum)
        if not risk_scores:
            return RiskLevel.SAFE
        
        max_score = max(risk_scores)
        return RiskLevel(max_score)
    
    def calculate_all_ssm(self, ego: EgoVehicle, obj: TrackedObject) -> SSMResult:
        """Calculate all SSM measures for an object.
        
        Args:
            ego: Ego vehicle state
            obj: Tracked object
            
        Returns:
            SSMResult with all calculated measures
        """
        eucl_dist, long_dist, lat_dist = self.calculate_distance(ego, obj)
        
        # Calculate individual SSMs
        ttc = self.calculate_ttc(ego, obj)
        ttc_2d = self.calculate_ttc_2d(ego, obj)
        drac = self.calculate_drac(ego, obj)
        mdr = self.calculate_mdr(ego, obj)
        
        # Use more conservative TTC
        final_ttc = None
        if ttc is not None and ttc_2d is not None:
            final_ttc = min(ttc, ttc_2d)
        elif ttc is not None:
            final_ttc = ttc
        elif ttc_2d is not None:
            final_ttc = ttc_2d
        
        # Relative velocity
        rel_vel = np.sqrt(obj.vx**2 + obj.vy**2)
        
        result = SSMResult(
            object_id=obj.object_id,
            ttc=final_ttc,
            ttc_inverse=1.0/final_ttc if final_ttc and final_ttc > 0.01 else None,
            drac=drac,
            mdr=mdr,
            distance=eucl_dist,
            relative_velocity=rel_vel
        )
        
        # Classify risk
        result.risk_level = self.classify_risk(result)
        
        return result
    
    def calculate_frame_ssm(self, frame: FrameData) -> List[SSMResult]:
        """Calculate SSM for all objects in a frame.
        
        Args:
            frame: Frame data containing ego and objects
            
        Returns:
            List of SSMResult for each object
        """
        results = []
        
        for obj in frame.objects:
            result = self.calculate_all_ssm(frame.ego, obj)
            results.append(result)
        
        return results
