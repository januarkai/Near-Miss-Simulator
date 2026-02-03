"""
Synthetic data generator for near-miss scenarios.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import random

from .scenario_types import (
    ScenarioType, TrackedObject, EgoVehicle, FrameData, ScenarioConfig, SCENARIO_CONFIGS
)

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Utils.config import (
    DataGeneratorConfig, ObjectClass, ObjectDimensions,
    DEFAULT_DATA_GENERATOR_CONFIG, DEFAULT_SIMULATION_CONFIG
)


class SyntheticDataGenerator:
    """Generates synthetic tracked object data for near-miss simulation."""
    
    def __init__(self, config: DataGeneratorConfig = None, sim_config = None):
        self.config = config or DEFAULT_DATA_GENERATOR_CONFIG
        self.sim_config = sim_config or DEFAULT_SIMULATION_CONFIG
        self.object_dims = ObjectDimensions()
        self.rng = np.random.default_rng()
        
    def set_seed(self, seed: int):
        """Set random seed for reproducibility."""
        self.rng = np.random.default_rng(seed)
        random.seed(seed)
        np.random.seed(seed)
        
    def get_object_dimensions(self, object_class: str) -> Tuple[float, float]:
        """Get length and width for an object class."""
        dims_map = {
            "car": self.object_dims.CAR,
            "truck": self.object_dims.TRUCK,
            "motorcycle": self.object_dims.MOTORCYCLE,
            "bicycle": self.object_dims.BICYCLE,
            "pedestrian": self.object_dims.PEDESTRIAN
        }
        return dims_map.get(object_class, self.object_dims.CAR)
    
    def sample_object_class(self) -> str:
        """Sample an object class based on distribution."""
        classes = list(self.config.class_distribution.keys())
        probs = list(self.config.class_distribution.values())
        return self.rng.choice(classes, p=probs)
    
    def sample_scenario_type(self) -> ScenarioType:
        """Sample a scenario type based on distribution."""
        types = list(self.config.scenario_distribution.keys())
        probs = list(self.config.scenario_distribution.values())
        scenario_name = self.rng.choice(types, p=probs)
        
        # Map string to enum
        type_map = {
            "normal_driving": ScenarioType.NORMAL_DRIVING,
            "car_following": ScenarioType.CAR_FOLLOWING,
            "lane_change": ScenarioType.LANE_CHANGE,
            "cut_in": ScenarioType.CUT_IN,
            "cut_out": ScenarioType.CUT_OUT,
            "crossing_pedestrian": ScenarioType.CROSSING_PEDESTRIAN,
            "approaching_stationary": ScenarioType.APPROACHING_STATIONARY,
            "near_miss_rear_end": ScenarioType.NEAR_MISS_REAR_END,
            "near_miss_side_swipe": ScenarioType.NEAR_MISS_SIDE_SWIPE
        }
        return type_map.get(scenario_name, ScenarioType.NORMAL_DRIVING)
    
    def generate_initial_object(self, object_id: int, scenario_type: ScenarioType,
                                role: str = "background") -> TrackedObject:
        """Generate an initial tracked object based on scenario and role."""
        
        # Sample object class
        if role == "lead":
            object_class = self.rng.choice(["car", "truck"], p=[0.8, 0.2])
        elif role == "adjacent":
            object_class = self.rng.choice(["car", "truck", "motorcycle"], p=[0.7, 0.2, 0.1])
        elif role == "pedestrian":
            object_class = "pedestrian"
        else:
            object_class = self.sample_object_class()
        
        length, width = self.get_object_dimensions(object_class)
        
        # Position based on role
        if role == "lead":
            x = self.rng.uniform(20, 60)
            y = self.rng.uniform(-0.5, 0.5)  # Same lane as ego
            vx = self.rng.uniform(-10, -2)  # Slower than ego
            vy = 0.0
        elif role == "adjacent":
            x = self.rng.uniform(-10, 30)
            lane = self.rng.choice([-1, 1])  # Left or right lane
            y = lane * self.sim_config.lane_width
            vx = self.rng.uniform(-5, 5)
            vy = 0.0
        elif role == "pedestrian":
            x = self.rng.uniform(30, 50)
            y = self.rng.choice([-1, 1]) * (self.sim_config.lane_width * 1.5 + 2)
            vx = -self.sim_config.ego_velocity  # Stationary in world frame
            vy = self.rng.choice([-1, 1]) * self.rng.uniform(1.0, 1.5)  # Walking speed
        else:
            # Background object
            x = self.rng.uniform(*self.config.longitudinal_range)
            y = self.rng.uniform(*self.config.lateral_range)
            vx = self.rng.uniform(*self.config.velocity_range)
            vy = self.rng.uniform(*self.config.lateral_velocity_range) * 0.1
        
        return TrackedObject(
            object_id=object_id,
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            length=length,
            width=width,
            object_class=object_class
        )
    
    def update_object_state(self, obj: TrackedObject, dt: float, 
                           scenario_type: ScenarioType, 
                           t: float, scenario_config: ScenarioConfig) -> TrackedObject:
        """Update object state for the next time step."""
        
        # Add noise
        noise_x = self.rng.normal(0, self.config.position_noise_std)
        noise_y = self.rng.normal(0, self.config.position_noise_std)
        noise_vx = self.rng.normal(0, self.config.velocity_noise_std)
        noise_vy = self.rng.normal(0, self.config.velocity_noise_std)
        
        # Check for lane change behavior
        if scenario_config.lane_change_start is not None:
            lc_start = scenario_config.lane_change_start
            lc_end = lc_start + scenario_config.lane_change_duration
            
            if lc_start <= t < lc_end:
                # During lane change
                progress = (t - lc_start) / scenario_config.lane_change_duration
                # Sinusoidal lateral velocity profile
                vy_lc = scenario_config.lane_change_direction * self.sim_config.lane_width / scenario_config.lane_change_duration
                vy_lc *= np.sin(np.pi * progress) * 1.5
                obj.vy = vy_lc
            else:
                obj.vy = 0.0
        
        # Update position
        new_x = obj.x + obj.vx * dt + noise_x
        new_y = obj.y + obj.vy * dt + noise_y
        
        # Update velocities with small noise
        new_vx = obj.vx + noise_vx
        new_vy = obj.vy + noise_vy
        
        return TrackedObject(
            object_id=obj.object_id,
            x=new_x,
            y=new_y,
            vx=new_vx,
            vy=new_vy,
            length=obj.length,
            width=obj.width,
            object_class=obj.object_class,
            heading=obj.heading
        )
    
    def generate_scenario(self, scenario_id: int, 
                         scenario_type: ScenarioType = None) -> List[FrameData]:
        """Generate a complete scenario with frame-by-frame data."""
        
        if scenario_type is None:
            scenario_type = self.sample_scenario_type()
        
        scenario_config = SCENARIO_CONFIGS.get(scenario_type, SCENARIO_CONFIGS[ScenarioType.NORMAL_DRIVING])
        
        # Initialize ego vehicle
        ego = EgoVehicle(
            vx=self.sim_config.ego_velocity,
            length=self.object_dims.EGO[0],
            width=self.object_dims.EGO[1]
        )
        
        # Generate initial objects
        objects = []
        obj_id = scenario_id * 100  # Unique IDs per scenario
        
        # Add role-specific objects
        if scenario_config.lead_vehicle:
            lead_obj = self.generate_initial_object(obj_id, scenario_type, "lead")
            lead_obj.x = scenario_config.lead_distance
            lead_obj.vx = scenario_config.lead_relative_velocity
            objects.append(lead_obj)
            obj_id += 1
        
        if scenario_config.adjacent_vehicle:
            adj_obj = self.generate_initial_object(obj_id, scenario_type, "adjacent")
            adj_obj.y = scenario_config.adjacent_lane * self.sim_config.lane_width
            adj_obj.x = scenario_config.adjacent_offset
            objects.append(adj_obj)
            obj_id += 1
        
        if scenario_type == ScenarioType.CROSSING_PEDESTRIAN:
            ped_obj = self.generate_initial_object(obj_id, scenario_type, "pedestrian")
            objects.append(ped_obj)
            obj_id += 1
        
        # Add background objects
        num_bg = max(0, scenario_config.num_objects - len(objects))
        for _ in range(num_bg):
            bg_obj = self.generate_initial_object(obj_id, scenario_type, "background")
            objects.append(bg_obj)
            obj_id += 1
        
        # Generate frames
        frames = []
        num_frames = int(scenario_config.duration / self.sim_config.dt)
        
        for frame_idx in range(num_frames):
            t = frame_idx * self.sim_config.dt
            
            # Create ground truth events
            ground_truth = []
            if scenario_config.near_miss_event and scenario_config.event_time:
                event_window = 0.5  # seconds
                if abs(t - scenario_config.event_time) < event_window:
                    ground_truth.append({
                        "type": "near_miss",
                        "scenario_type": scenario_type.value,
                        "time": scenario_config.event_time
                    })
            
            # Create frame data
            frame = FrameData(
                frame_id=frame_idx,
                timestamp=t,
                ego=ego,
                objects=[TrackedObject(**vars(obj)) for obj in objects],  # Deep copy
                ground_truth_events=ground_truth
            )
            frames.append(frame)
            
            # Update object states for next frame
            for i, obj in enumerate(objects):
                objects[i] = self.update_object_state(obj, self.sim_config.dt, 
                                                      scenario_type, t, scenario_config)
        
        return frames
    
    def generate_dataset(self, num_scenarios: int = None, 
                        seed: int = None) -> Dict[int, List[FrameData]]:
        """Generate a complete dataset with multiple scenarios."""
        
        if seed is not None:
            self.set_seed(seed)
        
        num_scenarios = num_scenarios or self.config.num_scenarios
        
        dataset = {}
        for scenario_id in range(num_scenarios):
            scenario_type = self.sample_scenario_type()
            frames = self.generate_scenario(scenario_id, scenario_type)
            dataset[scenario_id] = frames
        
        return dataset
    
    def generate_single_frame_batch(self, num_objects: int, 
                                    include_near_miss: bool = False) -> FrameData:
        """Generate a single frame with specified number of objects.
        
        Useful for quick testing or batch processing.
        """
        ego = EgoVehicle(vx=self.sim_config.ego_velocity)
        
        objects = []
        for obj_id in range(num_objects):
            obj = self.generate_initial_object(obj_id, ScenarioType.NORMAL_DRIVING, "background")
            objects.append(obj)
        
        # Optionally add a near-miss object
        if include_near_miss:
            nm_obj = TrackedObject(
                object_id=num_objects,
                x=15.0,  # Close ahead
                y=self.rng.uniform(-0.8, 0.8),  # In same lane
                vx=-8.0,  # Approaching fast
                vy=0.0,
                length=4.5,
                width=1.8,
                object_class="car"
            )
            objects.append(nm_obj)
        
        return FrameData(
            frame_id=0,
            timestamp=0.0,
            ego=ego,
            objects=objects,
            ground_truth_events=[{"type": "near_miss"}] if include_near_miss else []
        )
