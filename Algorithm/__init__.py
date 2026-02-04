"""Algorithm package initialization."""

from .base_algorithm import NearMissAlgorithm, ScenarioPrediction
from .registry import AlgorithmRegistry
from .ssm_calculator import SSMCalculator, SSMResult
from .trajectory_model import (
    TrajectoryModel,
    ConstantVelocityModel,
    ConstantAccelerationModel,
    CTRVModel,
    TrajectoryPredictor,
    PredictedState
)
from .near_miss_predictor import (
    NearMissPredictor,
    PredictionResult,
    ScenarioPrediction,
    ConflictType
)

__all__ = [
    'SSMCalculator',
    'SSMResult',
    'TrajectoryModel',
    'ConstantVelocityModel',
    'ConstantAccelerationModel',
    'CTRVModel',
    'TrajectoryPredictor',
    'PredictedState',
    'NearMissPredictor',
    'PredictionResult',
    'ScenarioPrediction',
    'ConflictType'
]
