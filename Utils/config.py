"""
Configuration parameters for the Near-Miss Prediction Simulator.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum


class RiskLevel(Enum):
    """Risk level classification."""
    SAFE = 0
    WARNING = 1
    NEAR_MISS = 2
    COLLISION = 3


class ObjectClass(Enum):
    """Object class types."""
    CAR = "car"
    TRUCK = "truck"
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    PEDESTRIAN = "pedestrian"
    EGO = "ego"


@dataclass
class ObjectDimensions:
    """Standard dimensions for different object classes (length, width in meters)."""
    CAR: Tuple[float, float] = (4.5, 1.8)
    TRUCK: Tuple[float, float] = (12.0, 2.5)
    MOTORCYCLE: Tuple[float, float] = (2.2, 0.8)
    BICYCLE: Tuple[float, float] = (1.8, 0.6)
    PEDESTRIAN: Tuple[float, float] = (0.5, 0.5)
    EGO: Tuple[float, float] = (4.5, 1.8)


@dataclass
class SSMThresholds:
    """Surrogate Safety Measures thresholds for risk classification.
    
    TTC (Time to Collision): in seconds
    DRAC (Deceleration Rate to Avoid Collision): in m/s²
    PET (Post-Encroachment Time): in seconds
    MDR (Minimum Distance Ratio): dimensionless
    """
    # TTC thresholds (lower is more dangerous)
    ttc_safe: float = 4.0
    ttc_warning: float = 2.0
    ttc_near_miss: float = 1.0
    ttc_collision: float = 0.0
    
    # DRAC thresholds (higher is more dangerous)
    drac_safe: float = 2.0
    drac_warning: float = 4.0
    drac_near_miss: float = 6.0
    drac_collision: float = 8.0
    
    # PET thresholds (lower is more dangerous)
    pet_safe: float = 2.0
    pet_warning: float = 1.0
    pet_near_miss: float = 0.5
    pet_collision: float = 0.0
    
    # MDR thresholds (lower is more dangerous)
    mdr_safe: float = 1.5
    mdr_warning: float = 1.0
    mdr_near_miss: float = 0.5
    mdr_collision: float = 0.0


@dataclass
class SimulationConfig:
    """Configuration for simulation parameters."""
    # Time parameters
    dt: float = 0.1  # Time step in seconds
    duration: float = 10.0  # Total simulation duration in seconds
    prediction_horizon: float = 3.0  # Prediction horizon in seconds
    
    # Spatial parameters (BEV)
    bev_width: float = 100.0  # BEV width in meters
    bev_height: float = 100.0  # BEV height in meters
    ego_position: Tuple[float, float] = (50.0, 10.0)  # Ego vehicle position (center-rear)
    
    # Lane parameters
    lane_width: float = 3.5  # Standard lane width in meters
    num_lanes: int = 3  # Number of lanes
    
    # Ego vehicle parameters
    ego_velocity: float = 15.0  # Ego velocity in m/s (about 54 km/h)
    
    # Minimum safe distance parameters
    min_longitudinal_gap: float = 2.0  # meters
    min_lateral_gap: float = 0.5  # meters
    
    # SSM thresholds
    ssm_thresholds: SSMThresholds = field(default_factory=SSMThresholds)


@dataclass
class DataGeneratorConfig:
    """Configuration for synthetic data generation."""
    # Number of scenarios
    num_scenarios: int = 100
    
    # Objects per scenario
    min_objects: int = 1
    max_objects: int = 10
    
    # Object class distribution (probabilities)
    class_distribution: Dict[str, float] = field(default_factory=lambda: {
        "car": 0.6,
        "truck": 0.15,
        "motorcycle": 0.1,
        "bicycle": 0.1,
        "pedestrian": 0.05
    })
    
    # Scenario type distribution
    scenario_distribution: Dict[str, float] = field(default_factory=lambda: {
        "normal_driving": 0.4,
        "car_following": 0.15,
        "lane_change": 0.15,
        "cut_in": 0.1,
        "cut_out": 0.05,
        "crossing_pedestrian": 0.05,
        "approaching_stationary": 0.05,
        "near_miss_rear_end": 0.025,
        "near_miss_side_swipe": 0.025
    })
    
    # Velocity ranges (m/s)
    velocity_range: Tuple[float, float] = (-10.0, 30.0)  # Relative to ego
    lateral_velocity_range: Tuple[float, float] = (-3.0, 3.0)
    
    # Position ranges (meters)
    longitudinal_range: Tuple[float, float] = (-20.0, 100.0)
    lateral_range: Tuple[float, float] = (-10.5, 10.5)  # 3 lanes each side
    
    # Near-miss event probability
    near_miss_probability: float = 0.2
    
    # Noise parameters
    position_noise_std: float = 0.1  # meters
    velocity_noise_std: float = 0.05  # m/s


@dataclass
class VisualizationConfig:
    """Configuration for BEV visualization."""
    # Window size
    window_width: int = 1200
    window_height: int = 800
    
    # BEV display area
    bev_margin: int = 50
    
    # Colors (RGB)
    background_color: Tuple[int, int, int] = (40, 40, 40)
    road_color: Tuple[int, int, int] = (60, 60, 60)
    lane_marking_color: Tuple[int, int, int] = (255, 255, 255)
    ego_color: Tuple[int, int, int] = (0, 150, 255)
    
    # Object colors by risk level
    risk_colors: Dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {
        "safe": (0, 255, 0),
        "warning": (255, 255, 0),
        "near_miss": (255, 165, 0),
        "collision": (255, 0, 0)
    })
    
    # Object colors by class
    class_colors: Dict[str, Tuple[int, int, int]] = field(default_factory=lambda: {
        "car": (100, 149, 237),
        "truck": (139, 69, 19),
        "motorcycle": (255, 20, 147),
        "bicycle": (0, 255, 127),
        "pedestrian": (255, 215, 0)
    })
    
    # Animation
    fps: int = 30
    playback_speed: float = 1.0


@dataclass
class EvaluationConfig:
    """Configuration for evaluation metrics."""
    # Ground truth labeling thresholds
    min_ttc_for_near_miss: float = 1.5
    min_distance_for_near_miss: float = 3.0
    
    # Evaluation window
    evaluation_window: float = 0.5  # seconds before/after event
    
    # Metrics to compute
    compute_precision: bool = True
    compute_recall: bool = True
    compute_f1: bool = True
    compute_fpr: bool = True
    compute_detection_time: bool = True


# Default configurations
DEFAULT_SIMULATION_CONFIG = SimulationConfig()
DEFAULT_DATA_GENERATOR_CONFIG = DataGeneratorConfig()
DEFAULT_VISUALIZATION_CONFIG = VisualizationConfig()
DEFAULT_EVALUATION_CONFIG = EvaluationConfig()
