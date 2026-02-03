"""
Scenario type definitions for synthetic data generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
import numpy as np


class ScenarioType(Enum):
    """Types of driving scenarios."""
    NORMAL_DRIVING = "normal_driving"
    CAR_FOLLOWING = "car_following"
    LANE_CHANGE = "lane_change"
    CUT_IN = "cut_in"
    CUT_OUT = "cut_out"
    CROSSING_PEDESTRIAN = "crossing_pedestrian"
    APPROACHING_STATIONARY = "approaching_stationary"
    NEAR_MISS_REAR_END = "near_miss_rear_end"
    NEAR_MISS_SIDE_SWIPE = "near_miss_side_swipe"
    NEAR_MISS_HEAD_ON = "near_miss_head_on"


@dataclass
class TrackedObject:
    """Represents a tracked object in the BEV space."""
    object_id: int
    x: float  # Longitudinal position (meters, relative to ego)
    y: float  # Lateral position (meters, relative to ego center)
    vx: float  # Longitudinal velocity (m/s, relative to ego)
    vy: float  # Lateral velocity (m/s)
    length: float  # Object length (meters)
    width: float  # Object width (meters)
    object_class: str  # Object type
    heading: float = 0.0  # Heading angle (radians, 0 = same direction as ego)
    
    def get_corners(self) -> np.ndarray:
        """Get the four corners of the object bounding box."""
        cos_h = np.cos(self.heading)
        sin_h = np.sin(self.heading)
        
        # Half dimensions
        hl = self.length / 2
        hw = self.width / 2
        
        # Corners in local frame
        corners_local = np.array([
            [hl, hw],   # front-left
            [hl, -hw],  # front-right
            [-hl, -hw], # rear-right
            [-hl, hw]   # rear-left
        ])
        
        # Rotation matrix
        R = np.array([[cos_h, -sin_h], [sin_h, cos_h]])
        
        # Transform to global frame
        corners_global = corners_local @ R.T + np.array([self.x, self.y])
        
        return corners_global
    
    def get_front_center(self) -> Tuple[float, float]:
        """Get the front center point of the object."""
        cos_h = np.cos(self.heading)
        sin_h = np.sin(self.heading)
        front_x = self.x + (self.length / 2) * cos_h
        front_y = self.y + (self.length / 2) * sin_h
        return front_x, front_y
    
    def get_rear_center(self) -> Tuple[float, float]:
        """Get the rear center point of the object."""
        cos_h = np.cos(self.heading)
        sin_h = np.sin(self.heading)
        rear_x = self.x - (self.length / 2) * cos_h
        rear_y = self.y - (self.length / 2) * sin_h
        return rear_x, rear_y


@dataclass
class EgoVehicle:
    """Represents the ego vehicle."""
    x: float = 0.0  # Always at origin in ego-centric frame
    y: float = 0.0
    vx: float = 0.0  # Ego velocity (absolute)
    vy: float = 0.0
    length: float = 4.5
    width: float = 1.8
    heading: float = 0.0
    
    def get_corners(self) -> np.ndarray:
        """Get the four corners of the ego vehicle."""
        hl = self.length / 2
        hw = self.width / 2
        
        return np.array([
            [hl, hw],   # front-left
            [hl, -hw],  # front-right
            [-hl, -hw], # rear-right
            [-hl, hw]   # rear-left
        ])


@dataclass
class FrameData:
    """Data for a single frame in the simulation."""
    frame_id: int
    timestamp: float
    ego: EgoVehicle
    objects: List[TrackedObject]
    ground_truth_events: List[Dict] = field(default_factory=list)


@dataclass
class ScenarioConfig:
    """Configuration for a specific scenario type."""
    scenario_type: ScenarioType
    duration: float  # seconds
    num_objects: int
    near_miss_event: bool = False
    event_time: Optional[float] = None  # When the near-miss occurs
    
    # Object placement parameters
    lead_vehicle: bool = False
    lead_distance: float = 30.0
    lead_relative_velocity: float = -5.0  # Approaching
    
    adjacent_vehicle: bool = False
    adjacent_lane: int = 1  # 1 = left, -1 = right
    adjacent_offset: float = 0.0  # Longitudinal offset from ego
    
    # Dynamics parameters
    lane_change_start: Optional[float] = None
    lane_change_duration: float = 3.0
    lane_change_direction: int = 0  # 1 = left, -1 = right


# Predefined scenario configurations
SCENARIO_CONFIGS = {
    ScenarioType.NORMAL_DRIVING: ScenarioConfig(
        scenario_type=ScenarioType.NORMAL_DRIVING,
        duration=10.0,
        num_objects=5,
        near_miss_event=False
    ),
    
    ScenarioType.CAR_FOLLOWING: ScenarioConfig(
        scenario_type=ScenarioType.CAR_FOLLOWING,
        duration=10.0,
        num_objects=3,
        near_miss_event=False,
        lead_vehicle=True,
        lead_distance=25.0,
        lead_relative_velocity=-2.0
    ),
    
    ScenarioType.LANE_CHANGE: ScenarioConfig(
        scenario_type=ScenarioType.LANE_CHANGE,
        duration=10.0,
        num_objects=4,
        near_miss_event=False,
        adjacent_vehicle=True,
        lane_change_start=3.0,
        lane_change_duration=3.0,
        lane_change_direction=1
    ),
    
    ScenarioType.CUT_IN: ScenarioConfig(
        scenario_type=ScenarioType.CUT_IN,
        duration=10.0,
        num_objects=3,
        near_miss_event=True,
        event_time=5.0,
        adjacent_vehicle=True,
        adjacent_lane=1,
        adjacent_offset=15.0,
        lane_change_start=3.0,
        lane_change_duration=2.5,
        lane_change_direction=-1  # Adjacent vehicle moving towards ego lane
    ),
    
    ScenarioType.CUT_OUT: ScenarioConfig(
        scenario_type=ScenarioType.CUT_OUT,
        duration=10.0,
        num_objects=4,
        near_miss_event=True,
        event_time=4.0,
        lead_vehicle=True,
        lead_distance=20.0,
        lane_change_start=2.0,
        lane_change_duration=2.0,
        lane_change_direction=1  # Lead vehicle moving out
    ),
    
    ScenarioType.CROSSING_PEDESTRIAN: ScenarioConfig(
        scenario_type=ScenarioType.CROSSING_PEDESTRIAN,
        duration=8.0,
        num_objects=2,
        near_miss_event=True,
        event_time=4.0
    ),
    
    ScenarioType.APPROACHING_STATIONARY: ScenarioConfig(
        scenario_type=ScenarioType.APPROACHING_STATIONARY,
        duration=10.0,
        num_objects=2,
        near_miss_event=True,
        event_time=6.0,
        lead_vehicle=True,
        lead_distance=60.0,
        lead_relative_velocity=-15.0  # Stationary = -ego_velocity
    ),
    
    ScenarioType.NEAR_MISS_REAR_END: ScenarioConfig(
        scenario_type=ScenarioType.NEAR_MISS_REAR_END,
        duration=10.0,
        num_objects=2,
        near_miss_event=True,
        event_time=5.0,
        lead_vehicle=True,
        lead_distance=40.0,
        lead_relative_velocity=-8.0  # Rapid approach
    ),
    
    ScenarioType.NEAR_MISS_SIDE_SWIPE: ScenarioConfig(
        scenario_type=ScenarioType.NEAR_MISS_SIDE_SWIPE,
        duration=10.0,
        num_objects=3,
        near_miss_event=True,
        event_time=5.0,
        adjacent_vehicle=True,
        adjacent_lane=1,
        adjacent_offset=0.0,
        lane_change_start=3.0,
        lane_change_duration=2.0,
        lane_change_direction=-1
    ),
    
    ScenarioType.NEAR_MISS_HEAD_ON: ScenarioConfig(
        scenario_type=ScenarioType.NEAR_MISS_HEAD_ON,
        duration=8.0,
        num_objects=2,
        near_miss_event=True,
        event_time=4.0
    )
}
