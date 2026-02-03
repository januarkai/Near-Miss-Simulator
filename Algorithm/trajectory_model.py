"""
Trajectory prediction models for near-miss detection.

Implements various trajectory prediction models:
- Constant Velocity (CV) Model
- Constant Acceleration (CA) Model
- Constant Turn Rate and Velocity (CTRV) Model
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Sources.scenario_types import TrackedObject, EgoVehicle


@dataclass
class PredictedState:
    """Predicted state at a future time."""
    timestamp: float
    x: float
    y: float
    vx: float
    vy: float
    heading: float = 0.0
    uncertainty_x: float = 0.0
    uncertainty_y: float = 0.0


class TrajectoryModel:
    """Base class for trajectory prediction models."""
    
    def __init__(self, dt: float = 0.1):
        self.dt = dt
    
    def predict(self, obj: TrackedObject, horizon: float) -> List[PredictedState]:
        """Predict trajectory over given horizon.
        
        Args:
            obj: Current object state
            horizon: Prediction horizon in seconds
            
        Returns:
            List of predicted states
        """
        raise NotImplementedError


class ConstantVelocityModel(TrajectoryModel):
    """Constant Velocity (CV) trajectory model.
    
    Assumes constant velocity throughout prediction horizon.
    x(t) = x0 + vx * t
    y(t) = y0 + vy * t
    """
    
    def __init__(self, dt: float = 0.1, process_noise_std: float = 0.5):
        super().__init__(dt)
        self.process_noise_std = process_noise_std
    
    def predict(self, obj: TrackedObject, horizon: float) -> List[PredictedState]:
        """Predict trajectory using constant velocity model."""
        predictions = []
        num_steps = int(horizon / self.dt)
        
        for i in range(1, num_steps + 1):
            t = i * self.dt
            
            # Position prediction
            x = obj.x + obj.vx * t
            y = obj.y + obj.vy * t
            
            # Uncertainty grows with time
            uncertainty = self.process_noise_std * np.sqrt(t)
            
            state = PredictedState(
                timestamp=t,
                x=x,
                y=y,
                vx=obj.vx,
                vy=obj.vy,
                heading=obj.heading,
                uncertainty_x=uncertainty,
                uncertainty_y=uncertainty
            )
            predictions.append(state)
        
        return predictions
    
    def predict_single(self, obj: TrackedObject, t: float) -> PredictedState:
        """Predict state at specific time t."""
        x = obj.x + obj.vx * t
        y = obj.y + obj.vy * t
        uncertainty = self.process_noise_std * np.sqrt(t)
        
        return PredictedState(
            timestamp=t,
            x=x,
            y=y,
            vx=obj.vx,
            vy=obj.vy,
            heading=obj.heading,
            uncertainty_x=uncertainty,
            uncertainty_y=uncertainty
        )


class ConstantAccelerationModel(TrajectoryModel):
    """Constant Acceleration (CA) trajectory model.
    
    Requires acceleration estimates.
    x(t) = x0 + vx * t + 0.5 * ax * t²
    y(t) = y0 + vy * t + 0.5 * ay * t²
    """
    
    def __init__(self, dt: float = 0.1, process_noise_std: float = 0.5):
        super().__init__(dt)
        self.process_noise_std = process_noise_std
        self.ax = 0.0  # Longitudinal acceleration
        self.ay = 0.0  # Lateral acceleration
    
    def set_acceleration(self, ax: float, ay: float):
        """Set acceleration values."""
        self.ax = ax
        self.ay = ay
    
    def estimate_acceleration(self, obj_history: List[TrackedObject]) -> Tuple[float, float]:
        """Estimate acceleration from object history.
        
        Args:
            obj_history: List of past object states (newest last)
            
        Returns:
            Tuple of (ax, ay) accelerations
        """
        if len(obj_history) < 2:
            return 0.0, 0.0
        
        # Use last two states to estimate acceleration
        dt = self.dt
        if len(obj_history) >= 2:
            ax = (obj_history[-1].vx - obj_history[-2].vx) / dt
            ay = (obj_history[-1].vy - obj_history[-2].vy) / dt
            return ax, ay
        
        return 0.0, 0.0
    
    def predict(self, obj: TrackedObject, horizon: float, 
                ax: float = None, ay: float = None) -> List[PredictedState]:
        """Predict trajectory using constant acceleration model."""
        if ax is None:
            ax = self.ax
        if ay is None:
            ay = self.ay
        
        predictions = []
        num_steps = int(horizon / self.dt)
        
        for i in range(1, num_steps + 1):
            t = i * self.dt
            
            # Position prediction with acceleration
            x = obj.x + obj.vx * t + 0.5 * ax * t**2
            y = obj.y + obj.vy * t + 0.5 * ay * t**2
            
            # Velocity at time t
            vx = obj.vx + ax * t
            vy = obj.vy + ay * t
            
            # Uncertainty grows faster with acceleration
            uncertainty = self.process_noise_std * np.sqrt(t) * (1 + abs(ax) + abs(ay)) * 0.5
            
            state = PredictedState(
                timestamp=t,
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                heading=obj.heading,
                uncertainty_x=uncertainty,
                uncertainty_y=uncertainty
            )
            predictions.append(state)
        
        return predictions


class CTRVModel(TrajectoryModel):
    """Constant Turn Rate and Velocity (CTRV) model.
    
    Useful for curved trajectories like lane changes.
    """
    
    def __init__(self, dt: float = 0.1, process_noise_std: float = 0.5):
        super().__init__(dt)
        self.process_noise_std = process_noise_std
    
    def predict(self, obj: TrackedObject, horizon: float, 
                omega: float = 0.0) -> List[PredictedState]:
        """Predict trajectory using CTRV model.
        
        Args:
            obj: Current object state
            horizon: Prediction horizon
            omega: Turn rate (rad/s)
            
        Returns:
            List of predicted states
        """
        predictions = []
        num_steps = int(horizon / self.dt)
        
        # Current state
        x = obj.x
        y = obj.y
        heading = obj.heading
        v = np.sqrt(obj.vx**2 + obj.vy**2)  # Speed magnitude
        
        for i in range(1, num_steps + 1):
            t = i * self.dt
            
            if abs(omega) > 0.001:
                # Curved motion
                x_new = x + v/omega * (np.sin(heading + omega*t) - np.sin(heading))
                y_new = y + v/omega * (np.cos(heading) - np.cos(heading + omega*t))
                heading_new = heading + omega * t
            else:
                # Straight motion (avoid division by zero)
                x_new = x + v * np.cos(heading) * t
                y_new = y + v * np.sin(heading) * t
                heading_new = heading
            
            vx_new = v * np.cos(heading_new)
            vy_new = v * np.sin(heading_new)
            
            # Uncertainty
            uncertainty = self.process_noise_std * np.sqrt(t) * (1 + abs(omega))
            
            state = PredictedState(
                timestamp=t,
                x=x_new,
                y=y_new,
                vx=vx_new,
                vy=vy_new,
                heading=heading_new,
                uncertainty_x=uncertainty,
                uncertainty_y=uncertainty
            )
            predictions.append(state)
        
        return predictions


class TrajectoryPredictor:
    """Multi-model trajectory predictor.
    
    Combines multiple models and selects best prediction based on context.
    """
    
    def __init__(self, dt: float = 0.1):
        self.dt = dt
        self.cv_model = ConstantVelocityModel(dt)
        self.ca_model = ConstantAccelerationModel(dt)
        self.ctrv_model = CTRVModel(dt)
    
    def predict_object(self, obj: TrackedObject, horizon: float,
                      obj_history: List[TrackedObject] = None) -> List[PredictedState]:
        """Predict object trajectory using most appropriate model.
        
        Args:
            obj: Current object state
            horizon: Prediction horizon
            obj_history: Historical states for acceleration estimation
            
        Returns:
            List of predicted states
        """
        # Determine best model based on motion characteristics
        speed = np.sqrt(obj.vx**2 + obj.vy**2)
        
        # If lateral velocity is significant, use CTRV
        if abs(obj.vy) > 0.5:
            # Estimate turn rate from lateral velocity
            if speed > 0.1:
                omega = obj.vy / (speed * 5)  # Simplified turn rate estimate
            else:
                omega = 0.0
            return self.ctrv_model.predict(obj, horizon, omega)
        
        # If we have history, check for acceleration
        if obj_history and len(obj_history) >= 2:
            ax, ay = self.ca_model.estimate_acceleration(obj_history)
            if abs(ax) > 0.5 or abs(ay) > 0.3:
                return self.ca_model.predict(obj, horizon, ax, ay)
        
        # Default to constant velocity
        return self.cv_model.predict(obj, horizon)
    
    def predict_collision_point(self, ego: EgoVehicle, obj: TrackedObject,
                               horizon: float = 5.0) -> Optional[Tuple[float, float, float]]:
        """Predict collision point between ego and object.
        
        Args:
            ego: Ego vehicle state
            obj: Object state
            horizon: Maximum prediction horizon
            
        Returns:
            Tuple of (x, y, time) of collision point, or None
        """
        # Predict trajectories
        ego_preds = self.cv_model.predict(
            TrackedObject(
                object_id=-1, x=0, y=0, vx=0, vy=0,
                length=ego.length, width=ego.width, object_class="ego"
            ),
            horizon
        )
        
        obj_preds = self.cv_model.predict(obj, horizon)
        
        # Find closest approach
        min_dist = float('inf')
        collision_time = None
        collision_point = None
        
        for ego_pred, obj_pred in zip(ego_preds, obj_preds):
            dist = np.sqrt((obj_pred.x - ego_pred.x)**2 + (obj_pred.y - ego_pred.y)**2)
            
            # Check for collision (overlap)
            safe_dist = (ego.length + obj.length) / 2
            
            if dist < safe_dist and dist < min_dist:
                min_dist = dist
                collision_time = obj_pred.timestamp
                collision_point = (obj_pred.x, obj_pred.y)
        
        if collision_point:
            return (*collision_point, collision_time)
        
        return None
