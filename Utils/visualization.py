"""
Bird's Eye View (BEV) Visualization for Near-Miss Simulator.

Provides real-time visualization of tracked objects and predictions.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Sources.scenario_types import TrackedObject, EgoVehicle, FrameData
from Algorithm.near_miss_predictor import PredictionResult, ConflictType
from Utils.config import (
    VisualizationConfig, RiskLevel, 
    DEFAULT_VISUALIZATION_CONFIG, DEFAULT_SIMULATION_CONFIG
)


class BEVVisualizer:
    """Bird's Eye View visualization using tkinter Canvas."""
    
    def __init__(self, config: VisualizationConfig = None, sim_config = None):
        self.config = config or DEFAULT_VISUALIZATION_CONFIG
        self.sim_config = sim_config or DEFAULT_SIMULATION_CONFIG
        
        # Canvas dimensions
        self.canvas_width = self.config.window_width - 400  # Leave space for info panel
        self.canvas_height = self.config.window_height - 100
        
        # BEV coordinate mapping
        # BEV: x = longitudinal (forward), y = lateral (left positive)
        # Canvas: x = right, y = down
        self.bev_x_range = (-20, 80)  # meters
        self.bev_y_range = (-15, 15)  # meters
        
        # Calculate scale
        self.scale_x = self.canvas_width / (self.bev_x_range[1] - self.bev_x_range[0])
        self.scale_y = self.canvas_height / (self.bev_y_range[1] - self.bev_y_range[0])
        self.scale = min(self.scale_x, self.scale_y)
        
        # UI components (initialized by create_canvas)
        self.canvas = None
        self.info_panel = None
        self.root = None
        
    def bev_to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        """Convert BEV coordinates to canvas coordinates.
        
        BEV: x forward, y left
        Canvas: x right, y down
        """
        # Center the view around ego (0,0 in BEV)
        canvas_x = (x - self.bev_x_range[0]) * self.scale
        canvas_y = self.canvas_height - (y - self.bev_y_range[0]) * self.scale
        
        return canvas_x, canvas_y
    
    def get_risk_color(self, risk_level: RiskLevel) -> str:
        """Get color for risk level."""
        color_map = {
            RiskLevel.SAFE: '#00FF00',
            RiskLevel.WARNING: '#FFFF00',
            RiskLevel.NEAR_MISS: '#FFA500',
            RiskLevel.COLLISION: '#FF0000'
        }
        return color_map.get(risk_level, '#FFFFFF')
    
    def get_class_color(self, object_class: str) -> str:
        """Get color for object class."""
        color_map = {
            'car': '#6495ED',
            'truck': '#8B4513',
            'motorcycle': '#FF1493',
            'bicycle': '#00FF7F',
            'pedestrian': '#FFD700'
        }
        return color_map.get(object_class, '#FFFFFF')
    
    def create_canvas(self, parent_frame: tk.Frame) -> tk.Canvas:
        """Create and return the BEV canvas widget."""
        self.canvas = tk.Canvas(
            parent_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self._rgb_to_hex(self.config.background_color)
        )
        return self.canvas
    
    def _rgb_to_hex(self, rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color string."""
        return f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
    
    def draw_road(self):
        """Draw road with lane markings."""
        if not self.canvas:
            return
        
        # Road background
        road_top_y = self.bev_to_canvas(0, 1.5 * self.sim_config.lane_width * self.sim_config.num_lanes / 2)[1]
        road_bottom_y = self.bev_to_canvas(0, -1.5 * self.sim_config.lane_width * self.sim_config.num_lanes / 2)[1]
        
        self.canvas.create_rectangle(
            0, road_top_y,
            self.canvas_width, road_bottom_y,
            fill=self._rgb_to_hex(self.config.road_color),
            outline=''
        )
        
        # Lane markings
        lane_width = self.sim_config.lane_width
        num_lanes = self.sim_config.num_lanes
        
        for i in range(-num_lanes, num_lanes + 1):
            y = i * lane_width / 2
            _, canvas_y = self.bev_to_canvas(0, y)
            
            # Edge lines (solid)
            if abs(i) == num_lanes:
                self.canvas.create_line(
                    0, canvas_y,
                    self.canvas_width, canvas_y,
                    fill='white', width=2
                )
            # Center line
            elif i == 0:
                self.canvas.create_line(
                    0, canvas_y,
                    self.canvas_width, canvas_y,
                    fill='yellow', width=2
                )
            # Lane dividers (dashed)
            else:
                # Draw dashed line
                dash_length = 30
                gap_length = 20
                x = 0
                while x < self.canvas_width:
                    self.canvas.create_line(
                        x, canvas_y,
                        min(x + dash_length, self.canvas_width), canvas_y,
                        fill='white', width=1
                    )
                    x += dash_length + gap_length
    
    def draw_ego_vehicle(self, ego: EgoVehicle):
        """Draw the ego vehicle."""
        if not self.canvas:
            return
        
        # Ego is at origin (0, 0)
        cx, cy = self.bev_to_canvas(0, 0)
        
        # Vehicle dimensions
        half_length = ego.length / 2 * self.scale
        half_width = ego.width / 2 * self.scale
        
        # Draw ego vehicle (rectangle)
        self.canvas.create_rectangle(
            cx - half_length, cy - half_width,
            cx + half_length, cy + half_width,
            fill=self._rgb_to_hex(self.config.ego_color),
            outline='white',
            width=2
        )
        
        # Draw direction indicator
        self.canvas.create_polygon(
            cx + half_length, cy,
            cx + half_length - 10, cy - 8,
            cx + half_length - 10, cy + 8,
            fill='white'
        )
        
        # Label
        self.canvas.create_text(
            cx, cy + half_width + 15,
            text='EGO',
            fill='white',
            font=('Arial', 10, 'bold')
        )
    
    def draw_tracked_object(self, obj: TrackedObject, 
                           prediction: PredictionResult = None):
        """Draw a tracked object with optional prediction info."""
        if not self.canvas:
            return
        
        # Get canvas coordinates
        cx, cy = self.bev_to_canvas(obj.x, obj.y)
        
        # Vehicle dimensions
        half_length = obj.length / 2 * self.scale
        half_width = obj.width / 2 * self.scale
        
        # Determine color
        if prediction and prediction.is_near_miss:
            fill_color = self.get_risk_color(prediction.risk_level)
            outline_width = 3
        else:
            fill_color = self.get_class_color(obj.object_class)
            outline_width = 1
        
        # Draw object rectangle
        rect_id = self.canvas.create_rectangle(
            cx - half_length, cy - half_width,
            cx + half_length, cy + half_width,
            fill=fill_color,
            outline='white',
            width=outline_width
        )
        
        # Draw velocity vector
        vel_scale = 5  # pixels per m/s
        vx_canvas = obj.vx * vel_scale
        vy_canvas = -obj.vy * vel_scale  # Flip for canvas coords
        
        if abs(vx_canvas) > 2 or abs(vy_canvas) > 2:
            self.canvas.create_line(
                cx, cy,
                cx + vx_canvas, cy + vy_canvas,
                fill='cyan', width=2, arrow=tk.LAST
            )
        
        # Draw ID label
        label = f"{obj.object_id}"
        self.canvas.create_text(
            cx, cy,
            text=label,
            fill='white',
            font=('Arial', 8)
        )
        
        # Draw prediction info if available
        if prediction and prediction.ttc is not None and prediction.ttc < 5.0:
            info_text = f"TTC:{prediction.ttc:.1f}s"
            self.canvas.create_text(
                cx, cy - half_width - 10,
                text=info_text,
                fill='white',
                font=('Arial', 8)
            )
    
    def draw_prediction_trajectory(self, obj: TrackedObject, horizon: float = 3.0):
        """Draw predicted trajectory for an object."""
        if not self.canvas:
            return
        
        # Constant velocity prediction
        points = []
        dt = 0.5
        num_steps = int(horizon / dt)
        
        for i in range(num_steps + 1):
            t = i * dt
            x = obj.x + obj.vx * t
            y = obj.y + obj.vy * t
            cx, cy = self.bev_to_canvas(x, y)
            points.append((cx, cy))
        
        # Draw trajectory line
        if len(points) >= 2:
            for i in range(len(points) - 1):
                alpha = 1.0 - i / len(points)  # Fade out
                color = f'#{int(150*alpha):02x}{int(150*alpha):02x}{int(150*alpha):02x}'
                self.canvas.create_line(
                    points[i][0], points[i][1],
                    points[i+1][0], points[i+1][1],
                    fill=color, width=1, dash=(2, 4)
                )
    
    def draw_frame(self, frame: FrameData, 
                  predictions: List[PredictionResult] = None):
        """Draw complete frame with all objects."""
        if not self.canvas:
            return
        
        # Clear canvas
        self.canvas.delete('all')
        
        # Draw road
        self.draw_road()
        
        # Draw distance markers
        self._draw_distance_markers()
        
        # Draw predicted trajectories
        for obj in frame.objects:
            self.draw_prediction_trajectory(obj)
        
        # Draw tracked objects
        pred_dict = {}
        if predictions:
            pred_dict = {p.object_id: p for p in predictions}
        
        for obj in frame.objects:
            pred = pred_dict.get(obj.object_id)
            self.draw_tracked_object(obj, pred)
        
        # Draw ego vehicle (on top)
        self.draw_ego_vehicle(frame.ego)
        
        # Draw frame info
        self._draw_frame_info(frame, predictions)
    
    def _draw_distance_markers(self):
        """Draw distance markers on the road."""
        for dist in [20, 40, 60, 80]:
            cx, cy = self.bev_to_canvas(dist, 0)
            self.canvas.create_line(
                cx, 0, cx, self.canvas_height,
                fill='#333333', width=1, dash=(5, 10)
            )
            self.canvas.create_text(
                cx + 5, 20,
                text=f'{dist}m',
                fill='#666666',
                font=('Arial', 8),
                anchor='w'
            )
    
    def _draw_frame_info(self, frame: FrameData, predictions: List[PredictionResult] = None):
        """Draw frame information overlay."""
        info_text = f"Frame: {frame.frame_id} | Time: {frame.timestamp:.2f}s"
        info_text += f" | Objects: {len(frame.objects)}"
        
        if predictions:
            nm_count = sum(1 for p in predictions if p.is_near_miss)
            if nm_count > 0:
                info_text += f" | ⚠ Near-Miss: {nm_count}"
        
        self.canvas.create_text(
            10, 10,
            text=info_text,
            fill='white',
            font=('Arial', 10),
            anchor='nw'
        )


class InfoPanel:
    """Information panel showing detailed prediction results."""
    
    def __init__(self, parent_frame: tk.Frame):
        self.frame = ttk.Frame(parent_frame)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(self.frame, text="Prediction Results", 
                 font=('Arial', 12, 'bold')).pack(pady=5)
        
        # Treeview for objects
        columns = ('ID', 'Class', 'Dist', 'TTC', 'Risk', 'Type')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=10)
        
        # Set column headers and widths
        self.tree.heading('ID', text='ID')
        self.tree.column('ID', width=30)
        
        self.tree.heading('Class', text='Class')
        self.tree.column('Class', width=60)
        
        self.tree.heading('Dist', text='Dist')
        self.tree.column('Dist', width=50)
        
        self.tree.heading('TTC', text='TTC')
        self.tree.column('TTC', width=40)
        
        self.tree.heading('Risk', text='Risk')
        self.tree.column('Risk', width=80)
        
        self.tree.heading('Type', text='Type')
        self.tree.column('Type', width=80)
        
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Summary labels
        self.summary_frame = ttk.LabelFrame(self.frame, text="Summary")
        self.summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.lbl_total = ttk.Label(self.summary_frame, text="Total Objects: 0")
        self.lbl_total.pack(anchor='w', padx=5)
        
        self.lbl_near_miss = ttk.Label(self.summary_frame, text="Near-Miss: 0")
        self.lbl_near_miss.pack(anchor='w', padx=5)
        
        self.lbl_min_ttc = ttk.Label(self.summary_frame, text="Min TTC: N/A")
        self.lbl_min_ttc.pack(anchor='w', padx=5)
        
        self.lbl_max_risk = ttk.Label(self.summary_frame, text="Max Risk: SAFE")
        self.lbl_max_risk.pack(anchor='w', padx=5)
        
        # Warning display
        self.warning_frame = ttk.LabelFrame(self.frame, text="Warnings")
        self.warning_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.warning_text = tk.Text(self.warning_frame, height=4, width=40)
        self.warning_text.pack(fill=tk.X, padx=5, pady=5)
        self.warning_text.config(state=tk.DISABLED)
    
    def update(self, predictions: List[PredictionResult]):
        """Update info panel with prediction results."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add prediction results
        near_miss_count = 0
        min_ttc = float('inf')
        max_risk = RiskLevel.SAFE
        warnings = []
        
        for pred in predictions:
            ttc_str = f"{pred.ttc:.1f}" if pred.ttc is not None else "N/A"
            risk_str = pred.risk_level.name
            
            # Format Conflict Type
            conflict_str = "None"
            if hasattr(pred, 'conflict_type') and pred.conflict_type:
                 # Check if it's an Enum or string
                 try:
                     val = pred.conflict_type.value
                 except AttributeError:
                     val = str(pred.conflict_type)
                 
                 if val != "none":
                     conflict_str = val.replace('_', ' ').title()

            # Add to tree
            tags = ()
            if pred.is_near_miss:
                tags = ('near_miss',)
            
            self.tree.insert('', 'end', values=(
                pred.object_id,
                pred.object_class,
                f"{pred.distance:.1f}",
                ttc_str,
                risk_str,
                conflict_str
            ), tags=tags)
            
            # Update stats
            if pred.is_near_miss:
                near_miss_count += 1
                warnings.append(pred.warning_message)
            
            if pred.ttc is not None and pred.ttc < min_ttc:
                min_ttc = pred.ttc
            
            if pred.risk_level.value > max_risk.value:
                max_risk = pred.risk_level
        
        # Style near-miss rows
        self.tree.tag_configure('near_miss', background='#FF6B6B')
        
        # Update summary
        self.lbl_total.config(text=f"Total Objects: {len(predictions)}")
        self.lbl_near_miss.config(text=f"Near-Miss: {near_miss_count}")
        self.lbl_min_ttc.config(text=f"Min TTC: {min_ttc:.1f}s" if min_ttc < float('inf') else "Min TTC: N/A")
        self.lbl_max_risk.config(text=f"Max Risk: {max_risk.name}")
        
        # Update warnings
        self.warning_text.config(state=tk.NORMAL)
        self.warning_text.delete('1.0', tk.END)
        if warnings:
            self.warning_text.insert('1.0', '\n'.join(warnings))
        else:
            self.warning_text.insert('1.0', 'No warnings')
        self.warning_text.config(state=tk.DISABLED)
