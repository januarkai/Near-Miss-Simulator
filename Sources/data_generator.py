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
        """Sample a scenario type. Always MIXED_NEAR_MISS per user request."""
        # User Requirement: Single scenario must contain all 5 types + negative examples.
        # This is handled by _generate_mixed_scenario entirely.
        return ScenarioType.MIXED_NEAR_MISS

        # --- OLD LOGIC COMMENTED OUT FOR NOW ---
        # near_miss_types = [
        #    ScenarioType.MIXED_NEAR_MISS, 
        #    ScenarioType.NEAR_MISS_REAR_END, ...
        
        safe_types = [
            ScenarioType.SAFE_REAR_END,
            ScenarioType.SAFE_LANE_CHANGE,
            ScenarioType.SAFE_CUT_OFF,
            ScenarioType.SAFE_BROADSIDE,
            ScenarioType.SAFE_RIGHT_OF_WAY,
            # ScenarioType.NORMAL_DRIVING, # Simplified for now
            # ScenarioType.CAR_FOLLOWING
        ]
        
        # 50% chance of Near-Miss vs Safe
        if self.rng.random() < 0.5:
            return self.rng.choice(near_miss_types)
        else:
            return self.rng.choice(safe_types)
    
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
        elif role == "crossing":
             object_class = self.rng.choice(["car", "truck", "motorcycle"], p=[0.7, 0.2, 0.1])
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
        elif role == "crossing":
            # Crossing vehicle (starts far, moves laterally)
            # Default to starting on left or right
            side = self.rng.choice([-1, 1])
            x = self.rng.uniform(30, 60) # Ahead
            y = side * (self.sim_config.lane_width * 3) # Far out
            vx = -self.sim_config.ego_velocity * 0.5 # Moving closer to ego longitudinally? Or purely crossing?
            # For broadside, it cuts across. 
            # If scenario config defines crossing props, they will be overwritten in generate_scenario usually.
            # But here initial stats:
            vy = -side * 5.0 # Moving towards center
            vx = 0.0 # Mostly lateral? Or slight longitudinal? 
            # Simulating crossing intersection often means maintaining absolute X or close to it, or moving relative.
            # Let's set initial here, but generate_scenario will likely override with scenario_config params.
            vx = -self.sim_config.ego_velocity # Stationary world X = moving relative -ego_v
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
            object_class=object_class,
            role=role  # Store role for behavior updates
        )
    
    def update_object_state(self, obj: TrackedObject, dt: float, 
                           scenario_type: ScenarioType, 
                           t: float, scenario_config: ScenarioConfig) -> TrackedObject:
        """Update object state for the next time step."""
        
        # INCREASED STOCHASTICITY (Random & Aggressive)
        # Multiply standard config noise by factors, and add random jerk (acceleration change)
        
        aggression_factor = 3.0 # Increase general noise
        
        noise_x = self.rng.normal(0, self.config.position_noise_std * aggression_factor)
        noise_y = self.rng.normal(0, self.config.position_noise_std * aggression_factor)
        
        # Velocity noise is acceleration integral, but let's just add noise to velocity directly
        noise_vx = self.rng.normal(0, self.config.velocity_noise_std * aggression_factor)
        noise_vy = self.rng.normal(0, self.config.velocity_noise_std * aggression_factor)
        
        # Occasional "Jerk" / Aggressive Maneuver (10% chance per frame)
        if self.rng.random() < 0.1:
            # Sudden acceleration or deceleration
            jerk_x = self.rng.uniform(-2.0, 2.0) # +/- 2 m/s^2 impulse
            noise_vx += jerk_x
        
        if self.rng.random() < 0.05:
            # Sudden swerve
            jerk_y = self.rng.uniform(-0.5, 0.5)
            noise_vy += jerk_y
        
        # Calculate kinematics
        new_vx = obj.vx + noise_vx
        new_vy = obj.vy + noise_vy
        
        # --- Behavior Logic ---
        
        # 1. Lane Change / Cut-In / Cut-Out (Lateral Movement)
        # Check either global config OR object-specific role/metadata implies a maneuver
        
        is_performing_lane_change = False
        lc_vy = 0.0
        
        # Standard Scenario Config Behavior (applied to 'adjacent' or 'lead' usually)
        if scenario_config.lane_change_start is not None:
             # This global config usually applies to the 'primary' actor. 
             # We check if this object is the intended actor.
             # In single-event scenarios, usually only 1 actor exists or we apply to specific ID/role.
             # Simplify: If scenario is NOT mixed, apply to relevant roles.
             
             apply_lc = False
             if scenario_type != ScenarioType.MIXED_NEAR_MISS:
                 if scenario_type in [ScenarioType.LANE_CHANGE, ScenarioType.NEAR_MISS_LANE_CHANGE, ScenarioType.SAFE_LANE_CHANGE]:
                     if obj.role == "adjacent": apply_lc = True
                 elif scenario_type in [ScenarioType.CUT_IN, ScenarioType.NEAR_MISS_CUTOFF, ScenarioType.SAFE_CUTOFF]:
                     if obj.role == "adjacent": apply_lc = True
                 elif scenario_type in [ScenarioType.CUT_OUT]:
                     if obj.role == "lead": apply_lc = True
            
             if apply_lc:
                lc_start = scenario_config.lane_change_start
                lc_end = lc_start + scenario_config.lane_change_duration
                
                if lc_start <= t < lc_end:
                    progress = (t - lc_start) / scenario_config.lane_change_duration
                    vy_amp = scenario_config.lane_change_direction * self.sim_config.lane_width / scenario_config.lane_change_duration
                    lc_vy = vy_amp * np.sin(np.pi * progress) * 1.5
                    new_vy = lc_vy # Override noise for controlled maneuver
                    is_performing_lane_change = True
        
        # 2. Mixed Scenario Behaviors (Per-Object)
        # MOVED TO THE MAIN LOOP to allow randomized timings
        
        # Update position
        new_x = obj.x + new_vx * dt + noise_x
        new_y = obj.y + new_vy * dt + noise_y
        
        # 3. Crossing Logic (Keep Vy constant/clean for crossing)
        if obj.role == "crossing" or obj.role.startswith("nm_broad") or obj.role.startswith("nm_right"):
             # reduce noise for crossing
             new_vy = obj.vy 
             new_vx = obj.vx
             new_y = obj.y + new_vy * dt
             new_x = obj.x + new_vx * dt

        return TrackedObject(
            object_id=obj.object_id,
            x=new_x,
            y=new_y,
            vx=new_vx,
            vy=new_vy,
            length=obj.length,
            width=obj.width,
            object_class=obj.object_class,
            heading=obj.heading,
            role=obj.role,
            is_risk_object=getattr(obj, 'is_risk_object', False)
        )
    
    def generate_scenario(self, scenario_id: int, 
                         scenario_type: ScenarioType = None) -> List[FrameData]:
        """Generate a complete scenario with frame-by-frame data."""
        
        if scenario_type is None:
            scenario_type = self.sample_scenario_type()
            
        # Handle Mixed Scenario Special Case
        if scenario_type == ScenarioType.MIXED_NEAR_MISS:
             return self._generate_mixed_scenario(scenario_id)
        
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
            
        if hasattr(scenario_config, 'crossing_vehicle') and scenario_config.crossing_vehicle:
            cross_obj = self.generate_initial_object(obj_id, scenario_type, "crossing")
            cross_obj.x = scenario_config.crossing_start_dist
            
            # Determine direction (Left to Right or Right to Left)
            start_side = self.rng.choice([-1, 1])
            cross_obj.y = start_side * (self.sim_config.lane_width * 3) # Start outside
            
            # Velocity: Crossing speed (Vy) and Longitudinal (Vx)
            # If perpendicular crossing, Vx relative to ego is -ego_v (to look stationary in world X)
            cross_obj.vx = -self.sim_config.ego_velocity 
            
            # Vy towards center
            cross_obj.vy = -start_side * scenario_config.crossing_velocity
             
            # Heading: Perpendicular
            cross_obj.heading = -start_side * np.pi / 2
            
            objects.append(cross_obj)
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
    
    def calculate_ttc(self, ego: EgoVehicle, obj: TrackedObject) -> float:
        """Calculate Time-To-Collision (TTC) between ego and object."""
        # 1. Longitudinal TTC
        # Relative distance (obj is at x relative to ego)
        # rel_dist = obj.x - ego.x (since ego.x is always 0 in simulation frame, dist = obj.x)
        rel_dist_x = obj.x 
        
        # Relative velocity (approach speed)
        # rel_vel = v_ego - v_obj 
        # (if ego=20, obj=15 -> rel_vel=5, closing in)
        # (if ego=20, obj=-5 -> rel_vel=25, closing fast)
        rel_vel_x = ego.vx - obj.vx
        
        ttc_x = float('inf')
        if rel_vel_x > 0.1: # Closing in
            ttc_x = rel_dist_x / rel_vel_x
            
        # 2. Lateral TTC (for crossing/cut-in)
        # rel_dist_y = obj.y - ego.y(0)
        rel_dist_y = abs(obj.y)
        # relative lateral velocity (assume ego vy=0 usually)
        rel_vel_y = abs(obj.vy) # simplistic for now
        
        ttc_y = float('inf')
        if rel_vel_y > 0.1 and (obj.y * obj.vy < 0): # Moving towards center (y=0)
             ttc_y = rel_dist_y / rel_vel_y
             
        # Combined TTC logic depends on scenario type, but simplistic min is often used
        # For this generator, we primarily use Longitudinal TTC as the trigger for Rear-End
        # For Crossing, we check if they will intersect.
        
        # Simpler robust check: 
        # If in same effective lane (lateral overlap), return TTC_x
        # Effective lane width approx 3.0m
        if abs(obj.y) < 1.8: 
            return ttc_x
            
        # If crossing (high lateral velocity), we care if they arrive at X=0 at similar time
        if abs(obj.vy) > 1.0:
            # Time for object to reach y=0
            time_to_center_y = abs(obj.y) / abs(obj.vy)
            
            # Where will ego be in that time? 
            # Ego travels d = v_ego * t
            # Object is currently at x. 
            # If (x - d) is small (collision), then it's a near miss. 
            # But this is Post-Encroachment Time (PET) prediction.
            
            # Let's stick to a simplified TTC for crossing:
            # Distance to conflict point
            dist_to_conflict = np.sqrt(obj.x**2 + obj.y**2)
            closing_speed = np.sqrt(rel_vel_x**2 + rel_vel_y**2)
            if closing_speed > 0.1:
                return dist_to_conflict / closing_speed
                
        return ttc_x
    
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

    def _generate_mixed_scenario(self, scenario_id: int) -> List[FrameData]:
        """Generate a complex scenario containing all 5 near-miss types + 5 Safe samples."""
        
        duration = 15.0 # Longer duration for all events
        num_frames = int(duration / self.sim_config.dt)
        objects = []
        obj_id = scenario_id * 100
        
        # --- POSITIVE SAMPLES (The 5 Required Near-Miss Types) ---
        
        # 1. Rear-End Object (Lead)
        rear_end_obj = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "lead")
        rear_end_obj.x = self.rng.uniform(35.0, 45.0) 
        rear_end_obj.vx = self.rng.uniform(-3.0, -1.0) # Slower than ego
        rear_end_obj.role = "nm_rear_end"
        rear_end_obj.is_risk_object = True
        objects.append(rear_end_obj)
        obj_id += 1
        
        # 2. Lane-Change Object (Definition 2: "Slow moving car... changing lanes")
        # Behavior: 15-20m ahead, 8-12 m/s slower, merges into ego lane
        lane_change_obj = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "adjacent")
        lane_change_obj.y = self.sim_config.lane_width  # Left lane
        lane_change_obj.x = self.rng.uniform(15.0, 25.0) 
        lane_change_obj.vx = self.rng.uniform(-12.0, -8.0) 
        lane_change_obj.role = "nm_lane_change"
        lane_change_obj.is_risk_object = True
        objects.append(lane_change_obj)
        obj_id += 1
        
        # 3. Cutoff Object (Definition 3: "Turning movement across path")
        # Behavior: Aggressive turn from right lane ahead
        cutoff_obj = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "adjacent")
        cutoff_obj.y = -self.sim_config.lane_width 
        cutoff_obj.vx = self.rng.uniform(-5.0, -2.0) 
        cutoff_obj.x = self.rng.uniform(20.0, 30.0) 
        cutoff_obj.role = "nm_cutoff"
        cutoff_obj.is_risk_object = True
        objects.append(cutoff_obj)
        obj_id += 1
        
        # 4. Broadside Object (Definition 4: "Vehicle crossing diagonally... T-bone")
        # Behavior: 40-50m ahead, crossing from left/right with high lateral speed
        broad_obj = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "crossing")
        broad_obj.x = self.rng.uniform(40.0, 50.0) 
        # Randomize direction (left-to-right or right-to-left)
        direction = 1 if self.rng.random() > 0.5 else -1
        broad_obj.y = direction * self.rng.uniform(12.0, 18.0) 
        broad_obj.vy = -direction * self.rng.uniform(6.0, 10.0) 
        broad_obj.vx = -self.sim_config.ego_velocity # Constant world position (crossing perpendicular)
        broad_obj.heading = -direction * np.pi / 2
        broad_obj.role = "nm_broadside"
        broad_obj.is_risk_object = True
        objects.append(broad_obj)
        obj_id += 1
        
        # 5. Right-of-Way Object (Definition 5: "Failure to yield at intersection")
        # Behavior: 50-60m ahead, waiting then suddenly accelerating into path
        row_obj = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "crossing")
        row_obj.x = self.rng.uniform(55.0, 65.0) 
        row_obj.y = -self.rng.uniform(6.0, 10.0) # Waiting at side street (right)
        row_obj.vx = -self.sim_config.ego_velocity # Initially stopped in world
        row_obj.vy = 0.0 # Initially stopped
        row_obj.heading = np.pi / 2
        row_obj.role = "nm_right_of_way"
        row_obj.is_risk_object = True
        objects.append(row_obj)
        obj_id += 1
        
        # --- NEGATIVE SAMPLES (5 Explicitly Safe Objects) ---
        
        # 6. Safe Lead (Background)
        safe_lead = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "background")
        safe_lead.x = 100.0 # Far ahead
        safe_lead.y = 0.0
        safe_lead.vx = 2.0 # Pulling away
        safe_lead.role = "safe_sample_1"
        objects.append(safe_lead)
        obj_id += 1
        
        # 7. Safe Parallel (Background)
        safe_parallel = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "background")
        safe_parallel.x = 10.0 
        safe_parallel.y = self.sim_config.lane_width * 2
        safe_parallel.vx = 0.0 # Matching speed
        safe_parallel.role = "safe_sample_2"
        objects.append(safe_parallel)
        obj_id += 1
        
        # 8. Safe Oncoming (Far lane)
        safe_oncoming = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "background")
        safe_oncoming.x = 80.0
        safe_oncoming.y = -self.sim_config.lane_width * 2
        safe_oncoming.vx = -20.0 # Fast pass (but far lane)
        safe_oncoming.role = "safe_sample_3"
        objects.append(safe_oncoming)
        obj_id += 1
        
        # 9. Static Object / Pedestrian (Safe distance)
        safe_static = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "background")
        safe_static.x = 120.0
        safe_static.y = -5.0 # Shoulder
        safe_static.vx = -self.sim_config.ego_velocity # Static in world
        safe_static.vy = 0.0 
        safe_static.role = "safe_sample_4"
        objects.append(safe_static)
        obj_id += 1
        
        # 10. Trailing Vehicle (Safe distance)
        safe_trail = self.generate_initial_object(obj_id, ScenarioType.MIXED_NEAR_MISS, "background")
        safe_trail.x = -50.0 
        safe_trail.y = 0.0
        safe_trail.vx = 0.0 
        safe_trail.role = "safe_sample_5"
        objects.append(safe_trail)
        obj_id += 1
        
        ego = EgoVehicle(vx=self.sim_config.ego_velocity)
        frames = []
        
        # Random timing offsets for this scenario instance
        t_ss_start = self.rng.uniform(1.0, 3.0)
        t_co_start = self.rng.uniform(4.5, 6.0)
        t_re_start = self.rng.uniform(3.0, 4.0)
        
        # Duration for events
        dur_ss = 3.0
        dur_co = 1.5
        dur_re = 3.0
        
        for frame_idx in range(num_frames):
            t = frame_idx * self.sim_config.dt
            
            # Ground Truth Generation (Physics-Based)
            ground_truth = []
            
            for obj in objects:
                if getattr(obj, 'is_risk_object', False):
                    # Skip if object is already behind us significantly
                    if obj.x < -5.0: 
                        continue
                        
                    ttc = self.calculate_ttc(ego, obj)
                    
                    # Enhanced Ground Truth Logic for Mixed Scenarios
                    # We use both physics (TTC) and the orchestrated event windows to ensure consistent labeling
                    
                    is_near_miss_frame = False
                    st_val = None
                    
                    # 1. Check Event Windows (Orchestrated)
                    if obj.role == "nm_rear_end":
                        # Rear end is always a potential threat as it approaches, 
                        # but specifically during the deceleration phase
                        st_val = ScenarioType.NEAR_MISS_REAR_END.value
                        if ttc < 3.0: 
                             is_near_miss_frame = True # Looser threshold than 2.5
                        if t_re_start <= t < t_re_start + dur_re: # During deceleration
                             is_near_miss_frame = True
                        
                    elif obj.role == "nm_lane_change":
                        st_val = ScenarioType.NEAR_MISS_LANE_CHANGE.value
                        # During the lane change maneuver
                        if t_ss_start <= t < t_ss_start + dur_ss:
                             is_near_miss_frame = True
                        elif ttc < 2.5: # Also count if dangerously close
                             is_near_miss_frame = True
                             
                    elif obj.role == "nm_cutoff":
                        st_val = ScenarioType.NEAR_MISS_CUTOFF.value
                        if t_co_start <= t < t_co_start + dur_co:
                             is_near_miss_frame = True
                        elif ttc < 2.5:
                             is_near_miss_frame = True
                    
                    elif obj.role == "nm_broadside":
                        st_val = ScenarioType.NEAR_MISS_BROADSIDE.value
                        # Broadside is continuous risk as it crosses
                        if ttc < 3.5: # Needs larger horizon for crossing
                             is_near_miss_frame = True
                             
                    elif obj.role == "nm_right_of_way":
                        st_val = ScenarioType.NEAR_MISS_RIGHT_OF_WAY.value
                        if ttc < 3.5:
                             is_near_miss_frame = True
                    
                    # 2. Add Event if Conditions Met
                    if is_near_miss_frame:
                         # Ensure TTC is recorded even if large
                         record_ttc = ttc if (ttc != float('inf') and ttc < 99) else 9.99
                         
                         if st_val == ScenarioType.NEAR_MISS_BROADSIDE.value:
                              # For broadside, force true if in range x < 30
                              if abs(obj.x) < 30.0: record_ttc = 1.5 
                         
                         ground_truth.append({
                            "type": "near_miss",
                            "scenario_type": st_val,
                            "time": t,
                            "object_id": obj.object_id,
                            "ttc": record_ttc
                        })
            
            frame = FrameData(
                frame_id=frame_idx,
                timestamp=t,
                ego=ego,
                objects=[TrackedObject(**vars(obj)) for obj in objects],
                ground_truth_events=ground_truth
            )
            frames.append(frame)
            
            for i, obj in enumerate(objects):
                # Apply Mixed Scenario Custom Logic with Randomized Timings
                
                # Check for maneuvers
                applied_custom_behavior = False
                
                if obj.role == "nm_lane_change":
                    if t_ss_start <= t < t_ss_start + dur_ss:
                         progress = (t - t_ss_start) / dur_ss
                         # Sine wave maneuver
                         lc_vy = (1.0 * self.sim_config.lane_width / dur_ss) * np.sin(np.pi * progress) * 1.5
                         obj.vy = lc_vy
                         applied_custom_behavior = True
                
                elif obj.role == "nm_cutoff":
                    if t_co_start <= t < t_co_start + dur_co:
                         progress = (t - t_co_start) / dur_co
                         lc_vy = (-1.0 * self.sim_config.lane_width / dur_co) * np.sin(np.pi * progress) * 1.5
                         obj.vy = lc_vy
                         applied_custom_behavior = True

                elif obj.role == "nm_broadside":
                     # Continuous crossing (constant velocity setup)
                     applied_custom_behavior = True

                elif obj.role == "nm_right_of_way":
                     # Wait until ego is close (relative x < 30m) then accelerate across
                     # obj.x is relative distance
                     if obj.x < 30.0 and obj.x > -10.0:
                         obj.vy = 8.0 # High acceleration/speed laterally
                     else:
                         obj.vy = 0.0
                     applied_custom_behavior = True
                
                elif obj.role == "nm_rear_end":
                    if t_re_start <= t < t_re_start + dur_re:
                         obj.vx -= 2.0 * self.sim_config.dt # Decelerate
                         applied_custom_behavior = True
                
                # Add Stochastic/Unpredictive Behavior (Aggressive Swerving & Jerky Movement)
                if not applied_custom_behavior:
                     # 1. Aggressive Acceleration Changes (Jerky throttle/braking)
                     # 20% chance to apply strong acceleration noise
                     if self.rng.random() < 0.20:
                         # Mix of small adjustments and sudden hard braking/gas
                         if self.rng.random() < 0.3:
                             acc_shock = self.rng.normal(0, 4.0) # Hard jerk (std=4 m/s^2)
                         else:
                             acc_shock = self.rng.normal(0, 1.5) # Normal adjustment
                         obj.vx += acc_shock * self.sim_config.dt
                         
                     # 2. Lateral Instability / Swerving (Drunk driver / Aggressive weaving)
                     # 10% chance to change immediate lateral velocity significantly
                     if self.rng.random() < 0.10:
                         # Random swerve
                         swerve = self.rng.normal(0, 0.8) # up to ~1-2 m/s lateral change
                         obj.vy += swerve
                     
                     # 3. Continuous Lane Wandering (sine wave roughly)
                     # Use object ID and time to create a deterministic but changing wobble
                     wobble_freq = 0.5 + (obj.object_id % 3) * 0.2
                     wobble_amp = 0.5 if obj.object_class == "motorcycle" else 0.2
                     obj.vy += wobble_amp * np.sin(2 * np.pi * wobble_freq * t) * self.sim_config.dt
                     
                     # Dampen vy if it gets too high (max 3 m/s lateral unless forced) to keep somewhat on road
                     max_vy = 4.0
                     obj.vy = np.clip(obj.vy, -max_vy, max_vy)

                     # Keep objects visually on screen (teleport if too far laterally? No, just bounce velocity)
                     if abs(obj.y) > 10.0: # ~3 lanes out
                         obj.vy += -0.5 * np.sign(obj.y) # Push back to center strongly
                
                # Call standard update for noise and physics integration
                objects[i] = self.update_object_state(obj, self.sim_config.dt, 
                                                      ScenarioType.MIXED_NEAR_MISS, t, SCENARIO_CONFIGS[ScenarioType.NORMAL_DRIVING])
        
        return frames
