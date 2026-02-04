"""
Base class for Near-Miss Algorithms.

Defines the interface that all near-miss detection algorithms must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from Sources.scenario_types import FrameData, ScenarioType
from dataclasses import dataclass, field
from Utils.config import SimulationConfig

@dataclass
class ScenarioPrediction:
    """Result of prediction for a full scenario."""
    scenario_id: int
    predictions: List[Any]  # List of frame-level PredictionResult
    near_miss_detected: bool
    first_detection_time: float = None
    max_risk_level: Any = None
    summary: Dict[str, Any] = field(default_factory=dict)

class NearMissAlgorithm(ABC):
    """Abstract base class for near-miss prediction algorithms."""
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config

    @property
    def name(self) -> str:
        """Return the display name of the algorithm. Defaults to class name."""
        return self.__class__.__name__

    @classmethod
    def get_name(cls) -> str:
        """Return the display name for registration (static)."""
        # Default to class name, override if needed
        return cls.__name__

    @abstractmethod
    def predict_scenario(self, scenario_id: int, frames: List[FrameData]) -> ScenarioPrediction:
        """
        Process a single scenario (list of frames) and return a prediction result.
        
        Args:
            scenario_id: Unique ID for the scenario
            frames: List of FrameData objects (chronological)
            
        Returns:
            ScenarioPrediction object
        """
        pass

    def predict_dataset(self, dataset: Dict[int, List[FrameData]]) -> Dict[int, ScenarioPrediction]:
        """
        Process an entire dataset.
        
        Args:
            dataset: Dictionary mapping scenario_id -> list of frames
            
        Returns:
            Dictionary mapping scenario_id -> ScenarioPrediction
        """
        results = {}
        for scenario_id, frames in dataset.items():
            results[scenario_id] = self.predict_scenario(scenario_id, frames)
        return results
