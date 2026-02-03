"""
Near-Miss Prediction Simulator GUI Application.

Main application window with:
- Synthetic data generation
- Custom scenario editor with object management
- Data import/export
- BEV visualization
- Prediction running
- Evaluation metrics display
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import copy

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Sources.data_generator import SyntheticDataGenerator
from Sources.data_loader import DataLoader
from Sources.scenario_types import FrameData, ScenarioType, TrackedObject, EgoVehicle
from Algorithm.near_miss_predictor import NearMissPredictor
from Utils.config import (
    DEFAULT_SIMULATION_CONFIG, DEFAULT_DATA_GENERATOR_CONFIG,
    DEFAULT_VISUALIZATION_CONFIG, SimulationConfig, DataGeneratorConfig
)
from Utils.visualization import BEVVisualizer, InfoPanel
from Utils.evaluation import Evaluator, EvaluationResults


class ObjectEditorDialog:
    """Dialog for adding/editing tracked objects."""
    
    def __init__(self, parent, title="Add Object", obj: TrackedObject = None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x500")
        # self.dialog.transient(parent)  # Removed to fix potential visibility issues
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._build_form(obj)
        
    def _build_form(self, obj: TrackedObject):
        """Build the form fields."""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Object ID
        row = 0
        ttk.Label(main_frame, text="Object ID:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky='w', pady=5)
        self.id_var = tk.StringVar(value=str(obj.object_id) if obj else "1")
        ttk.Entry(main_frame, textvariable=self.id_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        # Object Class
        row += 1
        ttk.Label(main_frame, text="Object Class:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky='w', pady=5)
        self.class_var = tk.StringVar(value=obj.object_class if obj else "car")
        class_combo = ttk.Combobox(main_frame, textvariable=self.class_var, 
                                   values=['car', 'truck', 'motorcycle', 'bicycle', 'pedestrian'],
                                   state='readonly', width=18)
        class_combo.grid(row=row, column=1, sticky='ew', pady=5, padx=(10, 0))
        
        # Position Section
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        ttk.Label(main_frame, text="Position", font=('Arial', 11, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        # X position
        row += 1
        ttk.Label(main_frame, text="X (longitudinal, m):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.x_var = tk.StringVar(value=str(obj.x) if obj else "20.0")
        ttk.Entry(main_frame, textvariable=self.x_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Y position
        row += 1
        ttk.Label(main_frame, text="Y (lateral, m):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.y_var = tk.StringVar(value=str(obj.y) if obj else "0.0")
        ttk.Entry(main_frame, textvariable=self.y_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Velocity Section
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        ttk.Label(main_frame, text="Velocity (relative to ego)", font=('Arial', 11, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        # Vx
        row += 1
        ttk.Label(main_frame, text="Vx (m/s):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.vx_var = tk.StringVar(value=str(obj.vx) if obj else "-5.0")
        ttk.Entry(main_frame, textvariable=self.vx_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Vy
        row += 1
        ttk.Label(main_frame, text="Vy (m/s):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.vy_var = tk.StringVar(value=str(obj.vy) if obj else "0.0")
        ttk.Entry(main_frame, textvariable=self.vy_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Dimensions Section
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=10)
        row += 1
        ttk.Label(main_frame, text="Dimensions", font=('Arial', 11, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(0, 5))
        
        # Length
        row += 1
        ttk.Label(main_frame, text="Length (m):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.length_var = tk.StringVar(value=str(obj.length) if obj else "4.5")
        ttk.Entry(main_frame, textvariable=self.length_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Width
        row += 1
        ttk.Label(main_frame, text="Width (m):").grid(
            row=row, column=0, sticky='w', pady=3)
        self.width_var = tk.StringVar(value=str(obj.width) if obj else "1.8")
        ttk.Entry(main_frame, textvariable=self.width_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Heading
        row += 1
        ttk.Label(main_frame, text="Heading (deg):").grid(
            row=row, column=0, sticky='w', pady=3)
        import math
        heading_deg = math.degrees(obj.heading) if obj else 0.0
        self.heading_var = tk.StringVar(value=str(heading_deg))
        ttk.Entry(main_frame, textvariable=self.heading_var, width=20).grid(
            row=row, column=1, sticky='ew', pady=3, padx=(10, 0))
        
        # Buttons
        row += 1
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, sticky='ew', pady=(20, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        
        ttk.Button(btn_frame, text="OK", command=self._on_ok, style='Big.TButton').grid(
            row=0, column=0, sticky='ew', padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=self._on_cancel).grid(
            row=0, column=1, sticky='ew', padx=(5, 0))
        
        main_frame.columnconfigure(1, weight=1)
        
    def _on_ok(self):
        """Handle OK button."""
        import math
        try:
            self.result = TrackedObject(
                object_id=int(self.id_var.get()),
                x=float(self.x_var.get()),
                y=float(self.y_var.get()),
                vx=float(self.vx_var.get()),
                vy=float(self.vy_var.get()),
                length=float(self.length_var.get()),
                width=float(self.width_var.get()),
                object_class=self.class_var.get(),
                heading=math.radians(float(self.heading_var.get()))
            )
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your input values:\n{e}")
            
    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = None
        self.dialog.destroy()
        
    def show(self) -> TrackedObject:
        """Show dialog and return result."""
        self.dialog.wait_window()
        return self.result


class ScenarioEditorDialog:
    """Dialog for creating/editing custom scenarios."""
    
    def __init__(self, parent, existing_dataset=None):
        self.parent = parent
        self.result = None
        self.frames = []  # List of FrameData
        self.current_frame_idx = 0
        
        print("DEBUG: ScenarioEditorDialog __init__ called")
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Scenario Editor")
        self.dialog.geometry("1000x750")
        # Removed transient to fix blank window issue on macOS
        # self.dialog.transient(parent)
        
        # FORCE white background
        self.dialog.configure(bg='white')
        
        print("DEBUG: Dialog created")
        
        # Initialize with existing data or empty frame
        if existing_dataset:
            first_key = list(existing_dataset.keys())[0]
            self.frames = copy.deepcopy(existing_dataset[first_key])
        else:
            self._add_empty_frame()
        
        print(f"DEBUG: Frames initialized: {len(self.frames)} frames")
        
        self._build_ui()
        print("DEBUG: UI built")
        self._update_display()
        print("DEBUG: Display updated")
        
        # Ensure window is ready/visible
        self.dialog.lift()
        self.dialog.focus_force()
        
    def _add_empty_frame(self):
        """Add an empty frame."""
        frame = FrameData(
            frame_id=len(self.frames),
            timestamp=len(self.frames) * 0.1,
            ego=EgoVehicle(vx=20.0),
            objects=[],  # Fixed: tracked_objects -> objects
            ground_truth_events=[]
        )
        # Inject missing attributes required by UI
        frame.scenario_type = ScenarioType.NORMAL_DRIVING
        frame.ground_truth_near_miss = False
        
        self.frames.append(frame)
        
    def _build_ui(self):
        """Build the editor UI with simplified robust layout."""
        print("DEBUG: Building UI...")
        
        # 1. HEADER
        tk.Label(self.dialog, text="Scenario Editor", 
                 font=('Arial', 18, 'bold'), bg='white', fg='black').pack(side=tk.TOP, fill=tk.X, pady=10)
        
        # 2. FOOTER (Buttons)
        bottom_frame = tk.Frame(self.dialog, bg='white', pady=10)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        tk.Button(bottom_frame, text="Cancel", font=('Arial', 12), command=self._cancel).pack(side=tk.RIGHT, padx=5)
        # Use black text for macOS compatibility
        tk.Button(bottom_frame, text="Save", font=('Arial', 12, 'bold'), command=self._save_scenario, 
                 bg='#4CAF50', fg='black').pack(side=tk.RIGHT, padx=5)
        
        # 3. CONTENT (Split View)
        # Use a colored frame to see if it takes space
        content_frame = tk.Frame(self.dialog, bg='#dddddd') 
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10)
        
        # Right Panel (Fixed width sidebar)
        right_panel = tk.Frame(content_frame, bg='#eeeeee', width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        # Ensure it has at least some size even if empty
        right_panel.pack_propagate(False) 
        
        # Left Panel (Main area)
        left_panel = tk.Frame(content_frame, bg='white')
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Populate panels
        try:
            self._build_left_simple(left_panel)
        except Exception as e:
            print(f"ERROR building left panel: {e}")
            tk.Label(left_panel, text=f"Error: {e}", fg='red').pack()

        try:
            self._build_right_simple(right_panel)
        except Exception as e:
            print(f"ERROR building right panel: {e}")
            tk.Label(right_panel, text=f"Error: {e}", fg='red').pack()

        # Force geometry update
        self.dialog.update()
        print("DEBUG: UI build complete and updated")

    def _build_left_simple(self, parent):
        """Build simplified left panel."""
        # 1. Frame Controls
        fc_frame = tk.LabelFrame(parent, text="Frame Controls", bg='white', fg='black', font=('Arial', 11, 'bold'))
        fc_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=5)
        
        f1 = tk.Frame(fc_frame, bg='white')
        f1.pack(fill=tk.X, padx=5)
        tk.Label(f1, text="Current Frame: ", bg='white', fg='black').pack(side=tk.LEFT)
        self.frame_label = tk.Label(f1, text="1 / 1", bg='white', fg='blue', font=('Arial', 12, 'bold'))
        self.frame_label.pack(side=tk.LEFT)
        
        f2 = tk.Frame(fc_frame, bg='white')
        f2.pack(fill=tk.X, padx=5, pady=5)
        
        # Navigation buttons
        for text, cmd in [("|<", self._first_frame), ("<", self._prev_frame), 
                          (">", self._next_frame), (">|", self._last_frame)]:
            tk.Button(f2, text=text, command=cmd, width=3).pack(side=tk.LEFT, padx=2)
        
        # Use black text for visibility on macOS
        tk.Button(f2, text="Add Frame", command=self._add_frame, bg='#4CAF50', fg='black').pack(side=tk.LEFT, padx=10)
        tk.Button(f2, text="Del Frame", command=self._delete_frame, bg='#f44336', fg='black').pack(side=tk.LEFT, padx=2)

        # 2. Settings
        set_frame = tk.LabelFrame(parent, text="Settings", bg='white', fg='black', font=('Arial', 11, 'bold'))
        set_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=5)
        
        # Helper to ensure packing works
        s1 = tk.Frame(set_frame, bg='white')
        s1.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(s1, text="Type:", bg='white', fg='black', width=6, anchor='w').pack(side=tk.LEFT)
        
        self.scenario_type_var = tk.StringVar(value="NORMAL_DRIVING")
        try:
            types = [st.name for st in ScenarioType]
            tk.OptionMenu(s1, self.scenario_type_var, *types, command=self._on_scenario_type_change_direct).pack(side=tk.LEFT, fill=tk.X, expand=True)
        except Exception as e:
            print(f"Error loading ScenarioTypes: {e}")
            tk.Label(s1, text="Error loading types").pack(side=tk.LEFT)
        
        s2 = tk.Frame(set_frame, bg='white')
        s2.pack(fill=tk.X, padx=5, pady=2)
        self.ground_truth_var = tk.BooleanVar(value=False)
        tk.Checkbutton(s2, text="Near-Miss Event", variable=self.ground_truth_var, bg='white', fg='black', 
                      command=self._on_ground_truth_change).pack(side=tk.LEFT)
        
        # Ego Speed Control
        s3 = tk.Frame(set_frame, bg='white')
        s3.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(s3, text="Ego Speed:", bg='white', fg='black').pack(side=tk.LEFT)
        self.ego_speed_var = tk.StringVar(value="20.0")
        tk.Entry(s3, textvariable=self.ego_speed_var, width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(s3, text="Set", command=self._on_ego_speed_change, width=5).pack(side=tk.LEFT)

        # FPS Control
        s4 = tk.Frame(set_frame, bg='white')
        s4.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(s4, text="FPS:", bg='white', fg='black').pack(side=tk.LEFT)
        self.fps_var = tk.StringVar(value="10")
        tk.Entry(s4, textvariable=self.fps_var, width=8).pack(side=tk.LEFT, padx=5)
                      
        # 3. Objects List
        list_frame = tk.LabelFrame(parent, text="Objects", bg='white', fg='black', font=('Arial', 11, 'bold'))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        sb = tk.Scrollbar(list_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.obj_listbox = tk.Listbox(list_frame, yscrollcommand=sb.set, font=('Courier', 11))
        self.obj_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.obj_listbox.yview)
        
        # 4. Actions
        act_frame = tk.Frame(parent, bg='white')
        act_frame.pack(fill=tk.X, pady=5)
        # Use black text for visibility on macOS
        tk.Button(act_frame, text="Add Object", bg='#2196F3', fg='black', command=self._add_object).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(act_frame, text="Edit", command=self._edit_object).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(act_frame, text="Remove", bg='#FF5722', fg='black', command=self._remove_object).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # 5. Quick Add
        qa_frame = tk.LabelFrame(parent, text="Quick Add", bg='white', fg='black', font=('Arial', 11, 'bold'))
        qa_frame.pack(fill=tk.X, pady=5)
        
        q1 = tk.Frame(qa_frame, bg='white')
        q1.pack(fill=tk.X, pady=2)
        tk.Button(q1, text="Car Front", command=lambda: self._quick_add('car_ahead')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(q1, text="Car Back", command=lambda: self._quick_add('car_behind')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        q2 = tk.Frame(qa_frame, bg='white')
        q2.pack(fill=tk.X, pady=2)
        tk.Button(q2, text="Pedestrian", command=lambda: self._quick_add('pedestrian')).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(q2, text="Trajectory...", command=self._generate_trajectory).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
    def _build_right_simple(self, parent):
        """Build simplified right panel."""
        tk.Label(parent, text="BEV Preview", font=('Arial', 12, 'bold'), 
                bg='white', fg='black').pack(anchor='w', pady=5)
        
        # Canvas
        self.preview_canvas = tk.Canvas(parent, width=280, height=400, bg='#2d5a3d',
                                        highlightthickness=1, highlightbackground='gray')
        self.preview_canvas.pack(pady=5)
        
        # Legend
        legend = tk.LabelFrame(parent, text="Legend", bg='white', fg='black', padx=5, pady=5)
        legend.pack(fill=tk.X, pady=5)
        
        items = [('EGO', '#4CAF50'), ('Car', '#FF5722'), ('Pedestrian', '#E91E63')]
        for name, color in items:
            row = tk.Frame(legend, bg='white')
            row.pack(anchor='w', pady=1)
            c = tk.Canvas(row, width=15, height=12, highlightthickness=0)
            c.pack(side=tk.LEFT)
            c.create_rectangle(2, 2, 13, 10, fill=color, outline='white')
            tk.Label(row, text=f"  {name}", bg='white', fg='black').pack(side=tk.LEFT)
    
    def _on_scenario_type_change_direct(self, value):
        """Handle scenario type change from OptionMenu."""
        if self.frames:
            self.frames[self.current_frame_idx].scenario_type = ScenarioType[value]
            
    def _copy_objects_to_all(self):
        """Copy current frame's objects to all frames."""
        if not self.frames:
            return
        current_objects = copy.deepcopy(self.frames[self.current_frame_idx].objects)
        for frame in self.frames:
            frame.objects = copy.deepcopy(current_objects)
        messagebox.showinfo("Done", f"Copied {len(current_objects)} objects to all {len(self.frames)} frames.")
            
    def _update_display(self):
        """Update the display with current frame data."""
        if not self.frames:
            return
            
        frame = self.frames[self.current_frame_idx]
        
        # Update frame label
        self.frame_label.config(text=f"{self.current_frame_idx + 1} / {len(self.frames)}")
        
        # Update settings
        self.scenario_type_var.set(frame.scenario_type.name)
        self.ground_truth_var.set(frame.ground_truth_near_miss)
        self.ego_speed_var.set(str(frame.ego.vx))
        
        # Update object listbox
        self.obj_listbox.delete(0, tk.END)
        self.obj_listbox.insert(tk.END, f"{'ID':<4} {'Class':<12} {'X':>8} {'Y':>8} {'Vx':>8} {'Vy':>8}")
        self.obj_listbox.insert(tk.END, "-" * 60)
        
        for obj in frame.objects:
            line = f"{obj.object_id:<4} {obj.object_class:<12} {obj.x:>8.1f} {obj.y:>8.1f} {obj.vx:>8.1f} {obj.vy:>8.1f}"
            self.obj_listbox.insert(tk.END, line)
        
        # Update preview
        self._draw_preview()
        
        print(f"DEBUG: Display updated - Frame {self.current_frame_idx + 1}/{len(self.frames)}, {len(frame.objects)} objects")
        
    def _draw_preview(self):
        """Draw the BEV preview."""
        self.preview_canvas.delete('all')
        
        if not self.frames:
            return
            
        frame = self.frames[self.current_frame_idx]
        
        # Canvas dimensions
        cw, ch = 300, 450
        
        # Scale: 1 meter = 5 pixels
        scale = 5
        
        # Road (centered)
        road_width = 80
        self.preview_canvas.create_rectangle(
            (cw - road_width) // 2, 0, (cw + road_width) // 2, ch,
            fill='#404040', outline=''
        )
        
        # Lane lines
        for i in range(-1, 2):
            x = cw // 2 + i * 20
            dash = (10, 10) if i == 0 else ()
            color = 'yellow' if i == 0 else 'white'
            self.preview_canvas.create_line(x, 0, x, ch, fill=color, dash=dash, width=2)
        
        # Ego vehicle (centered, bottom third)
        ego_cx, ego_cy = cw // 2, ch - 80
        ego_w, ego_h = int(frame.ego.width * scale), int(frame.ego.length * scale)
        self.preview_canvas.create_rectangle(
            ego_cx - ego_w // 2, ego_cy - ego_h // 2,
            ego_cx + ego_w // 2, ego_cy + ego_h // 2,
            fill='#4CAF50', outline='white', width=2
        )
        self.preview_canvas.create_text(ego_cx, ego_cy, text="EGO", fill='white', font=('Arial', 8, 'bold'))
        
        # Draw tracked objects
        for obj in frame.objects:
            # Convert object position to canvas coordinates
            # X (longitudinal) maps to vertical (positive = ahead = up)
            # Y (lateral) maps to horizontal (positive = left)
            obj_cx = ego_cx - int(obj.y * scale)  # Flip Y for canvas
            obj_cy = ego_cy - int(obj.x * scale)  # Flip X for canvas (ahead = up)
            
            obj_w = int(obj.width * scale)
            obj_h = int(obj.length * scale)
            
            # Color based on class
            colors = {
                'car': '#FF5722', 'truck': '#FF9800', 
                'motorcycle': '#9C27B0', 'bicycle': '#2196F3',
                'pedestrian': '#E91E63'
            }
            color = colors.get(obj.object_class, '#FF5722')
            
            self.preview_canvas.create_rectangle(
                obj_cx - obj_w // 2, obj_cy - obj_h // 2,
                obj_cx + obj_w // 2, obj_cy + obj_h // 2,
                fill=color, outline='white', width=1
            )
            self.preview_canvas.create_text(
                obj_cx, obj_cy, text=str(obj.object_id), 
                fill='white', font=('Arial', 7, 'bold')
            )
    
    def _first_frame(self):
        self.current_frame_idx = 0
        self._update_display()
        
    def _prev_frame(self):
        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self._update_display()
            
    def _next_frame(self):
        if self.current_frame_idx < len(self.frames) - 1:
            self.current_frame_idx += 1
            self._update_display()
            
    def _last_frame(self):
        self.current_frame_idx = len(self.frames) - 1
        self._update_display()
        
    def _add_frame(self):
        """Add a new frame (based on last frame with physics update)."""
        if self.frames:
            # Get FPS & Calculate dt
            try:
                fps = float(self.fps_var.get())
                if fps <= 0: fps = 10.0
            except (ValueError, AttributeError):
                fps = 10.0
            dt = 1.0 / fps

            # Use the LAST frame as the base for continuity
            base_frame = self.frames[-1]
            new_frame = copy.deepcopy(base_frame)
            
            new_frame.frame_id = len(self.frames)
            new_frame.timestamp = base_frame.timestamp + dt
            
            # Update object positions based on relative velocities
            # x_new = x_old + vx * dt
            # y_new = y_old + vy * dt
            for obj in new_frame.objects:
                obj.x += obj.vx * dt
                obj.y += obj.vy * dt
            
            self.frames.append(new_frame)
        else:
            self._add_empty_frame()
        self.current_frame_idx = len(self.frames) - 1
        self._update_display()
        
    def _delete_frame(self):
        """Delete current frame."""
        if len(self.frames) <= 1:
            messagebox.showwarning("Warning", "Cannot delete the last frame.")
            return
        
        self.frames.pop(self.current_frame_idx)
        # Renumber frames
        for i, f in enumerate(self.frames):
            f.frame_id = i
            f.timestamp = i * 0.1
            
        if self.current_frame_idx >= len(self.frames):
            self.current_frame_idx = len(self.frames) - 1
        self._update_display()
        
    def _on_scenario_type_change_direct(self, value):
        """Handle scenario type change directly from OptionMenu."""
        if self.frames:
            self.frames[self.current_frame_idx].scenario_type = ScenarioType[value]

    def _on_scenario_type_change(self, event):
        """Handle scenario type change."""
        if self.frames:
            self.frames[self.current_frame_idx].scenario_type = ScenarioType[self.scenario_type_var.get()]
            
    def _on_ground_truth_change(self):
        """Handle ground truth change."""
        if self.frames:
            self.frames[self.current_frame_idx].ground_truth_near_miss = self.ground_truth_var.get()
            
    def _on_ego_speed_change(self, event=None):
        """Handle ego speed change."""
        if self.frames:
            try:
                speed = float(self.ego_speed_var.get())
                self.frames[self.current_frame_idx].ego.vx = speed
            except ValueError:
                pass
    
    def _add_object(self):
        """Add a new object."""
        # Find next available ID
        existing_ids = set()
        for frame in self.frames:
            for obj in frame.objects:
                existing_ids.add(obj.object_id)
        next_id = 1
        while next_id in existing_ids:
            next_id += 1
            
        dialog = ObjectEditorDialog(self.dialog, "Add Object", 
                                    TrackedObject(next_id, 20.0, 0.0, -5.0, 0.0, 4.5, 1.8, 'car'))
        result = dialog.show()
        
        if result:
            self.frames[self.current_frame_idx].objects.append(result)
            self._update_display()
            
    def _edit_object(self):
        """Edit selected object."""
        selection = self.obj_listbox.curselection()
        if not selection or selection[0] < 2:  # Skip header rows
            messagebox.showwarning("Warning", "Please select an object to edit.")
            return
            
        # Get the actual object index (subtract 2 for header)
        obj_idx = selection[0] - 2
        
        frame = self.frames[self.current_frame_idx]
        if 0 <= obj_idx < len(frame.objects):
            obj = frame.objects[obj_idx]
            dialog = ObjectEditorDialog(self.dialog, "Edit Object", obj)
            result = dialog.show()
            if result:
                frame.objects[obj_idx] = result
                self._update_display()
                
    def _remove_object(self):
        """Remove selected object."""
        selection = self.obj_listbox.curselection()
        if not selection or selection[0] < 2:  # Skip header rows
            messagebox.showwarning("Warning", "Please select an object to remove.")
            return
            
        # Get the actual object index (subtract 2 for header)
        obj_idx = selection[0] - 2
        
        frame = self.frames[self.current_frame_idx]
        if 0 <= obj_idx < len(frame.objects):
            frame.objects.pop(obj_idx)
            self._update_display()
            self._update_display()
        
    def _quick_add(self, preset: str):
        """Quick add preset objects."""
        # Find next available ID
        existing_ids = set()
        for frame in self.frames:
            for obj in frame.objects:
                existing_ids.add(obj.object_id)
        next_id = 1
        while next_id in existing_ids:
            next_id += 1
            
        presets = {
            'car_ahead': TrackedObject(next_id, 25.0, 0.0, -3.0, 0.0, 4.5, 1.8, 'car'),
            'car_behind': TrackedObject(next_id, -15.0, 0.0, 5.0, 0.0, 4.5, 1.8, 'car'),
            'car_left': TrackedObject(next_id, 10.0, 3.5, -2.0, 0.0, 4.5, 1.8, 'car'),
            'car_right': TrackedObject(next_id, 10.0, -3.5, -2.0, 0.0, 4.5, 1.8, 'car'),
            'pedestrian': TrackedObject(next_id, 30.0, 5.0, 0.0, -1.5, 0.5, 0.5, 'pedestrian'),
            'motorcycle': TrackedObject(next_id, 15.0, 2.0, -4.0, 0.0, 2.2, 0.8, 'motorcycle'),
        }
        
        if preset in presets:
            self.frames[self.current_frame_idx].objects.append(presets[preset])
            self._update_display()
            
    def _generate_trajectory(self):
        """Generate trajectory for all objects across frames."""
        if not self.frames or not self.frames[0].objects:
            messagebox.showwarning("Warning", "Add at least one object first.")
            return
            
        # Get number of frames from entry
        try:
            num_frames = int(self.traj_frames_var.get())
            if num_frames < 2:
                num_frames = 50
        except (ValueError, AttributeError):
            num_frames = 50
            
        # Get first frame as template
        template = self.frames[0]
        dt = 0.1  # 100ms per frame
        
        # Generate frames
        self.frames = []
        for i in range(num_frames):
            frame = FrameData(
                frame_id=i,
                timestamp=i * dt,
                ego=EgoVehicle(vx=template.ego.vx),
                objects=[],
                ground_truth_events=template.ground_truth_events
            )
            # Inject attributes
            frame.scenario_type = template.scenario_type
            frame.ground_truth_near_miss = template.ground_truth_near_miss
            
            # Update object positions based on velocity
            for obj in template.objects:
                new_obj = TrackedObject(
                    object_id=obj.object_id,
                    x=obj.x + obj.vx * i * dt,
                    y=obj.y + obj.vy * i * dt,
                    vx=obj.vx,
                    vy=obj.vy,
                    length=obj.length,
                    width=obj.width,
                    object_class=obj.object_class,
                    heading=obj.heading
                )
                frame.objects.append(new_obj)
                
            self.frames.append(frame)
            
        self.current_frame_idx = 0
        self._update_display()
        messagebox.showinfo("Success", f"Generated {num_frames} frames with trajectory.")
            
    def _save_scenario(self):
        """Save the scenario."""
        if not self.frames:
            messagebox.showerror("Error", "No frames to save.")
            return
            
        self.result = self.frames
        self.dialog.destroy()
        
    def _cancel(self):
        """Cancel and close."""
        self.result = None
        self.dialog.destroy()
        
    def show(self):
        """Show dialog and return result."""
        self.dialog.wait_window()
        return self.result


class SimulatorApp:
    """Main simulator application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Near-Miss Prediction Simulator")
        self.root.geometry("1600x900")
        self.root.minsize(1400, 800)
        
        # Configuration
        self.sim_config = DEFAULT_SIMULATION_CONFIG
        self.gen_config = DEFAULT_DATA_GENERATOR_CONFIG
        self.vis_config = DEFAULT_VISUALIZATION_CONFIG
        
        # Components
        self.data_generator = SyntheticDataGenerator(self.gen_config, self.sim_config)
        self.data_loader = DataLoader()
        self.predictor = NearMissPredictor(self.sim_config)
        self.evaluator = Evaluator()
        
        # Data
        self.current_dataset = None
        self.current_scenario_id = None
        self.current_frame_idx = 0
        self.current_predictions = None
        self.evaluation_results = None
        
        # Playback state
        self.is_playing = False
        self.playback_speed = 1.0
        
        # Configure styles
        self._configure_styles()
        
        # Build UI
        self._build_ui()
        
    def _configure_styles(self):
        """Configure ttk styles for better appearance."""
        style = ttk.Style()
        
        # Configure button padding
        style.configure('TButton', padding=(8, 4))
        style.configure('Big.TButton', padding=(12, 8), font=('Arial', 10))
        style.configure('TLabelframe.Label', font=('Arial', 10, 'bold'))
        
    def _build_ui(self):
        """Build the main UI using grid layout."""
        # Configure root grid
        self.root.columnconfigure(0, weight=0, minsize=300)   # Left panel - fixed width
        self.root.columnconfigure(1, weight=1, minsize=600)   # Center panel - expandable
        self.root.columnconfigure(2, weight=0, minsize=350)   # Right panel - fixed width
        self.root.rowconfigure(0, weight=1)
        
        # ===== LEFT PANEL - Controls =====
        left_frame = ttk.Frame(self.root, padding=5)
        left_frame.grid(row=0, column=0, sticky='nsew')
        left_frame.columnconfigure(0, weight=1)
        self._build_control_panel(left_frame)
        
        # ===== CENTER PANEL - BEV Visualization =====
        center_frame = ttk.Frame(self.root, padding=5)
        center_frame.grid(row=0, column=1, sticky='nsew')
        center_frame.columnconfigure(0, weight=1)
        center_frame.rowconfigure(1, weight=1)
        self._build_visualization_panel(center_frame)
        
        # ===== RIGHT PANEL - Info =====
        right_frame = ttk.Frame(self.root, padding=5)
        right_frame.grid(row=0, column=2, sticky='nsew')
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        self._build_info_panel(right_frame)
        
    def _build_control_panel(self, parent: ttk.Frame):
        """Build the control panel on the left."""
        row = 0
        
        # Title
        title = ttk.Label(parent, text="Controls", font=('Arial', 14, 'bold'))
        title.grid(row=row, column=0, sticky='w', pady=(0, 15))
        row += 1
        
        # ===== Data Generation Section =====
        gen_frame = ttk.LabelFrame(parent, text="Data Generation", padding=10)
        gen_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        gen_frame.columnconfigure(1, weight=1)
        row += 1
        
        # Scenarios
        ttk.Label(gen_frame, text="Scenarios:").grid(row=0, column=0, sticky='w', pady=3)
        self.num_scenarios_var = tk.StringVar(value="10")
        scenarios_entry = ttk.Entry(gen_frame, textvariable=self.num_scenarios_var, width=15)
        scenarios_entry.grid(row=0, column=1, sticky='e', pady=3, padx=(10, 0))
        
        # Seed
        ttk.Label(gen_frame, text="Random Seed:").grid(row=1, column=0, sticky='w', pady=3)
        self.seed_var = tk.StringVar(value="42")
        seed_entry = ttk.Entry(gen_frame, textvariable=self.seed_var, width=15)
        seed_entry.grid(row=1, column=1, sticky='e', pady=3, padx=(10, 0))
        
        # Generate button
        gen_btn = ttk.Button(gen_frame, text="Generate Data", 
                            command=self._on_generate, style='Big.TButton')
        gen_btn.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        
        # Custom scenario button
        custom_btn = ttk.Button(gen_frame, text="Create Custom Scenario", 
                               command=self._on_create_custom)
        custom_btn.grid(row=3, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        
        # Edit current scenario button
        edit_btn = ttk.Button(gen_frame, text="Edit Current Scenario", 
                             command=self._on_edit_scenario)
        edit_btn.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(5, 0))
        
        # ===== Data I/O Section =====
        io_frame = ttk.LabelFrame(parent, text="Import / Export", padding=10)
        io_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        io_frame.columnconfigure(0, weight=1)
        io_frame.columnconfigure(1, weight=1)
        row += 1
        
        ttk.Button(io_frame, text="Export CSV", 
                  command=self._on_export).grid(row=0, column=0, sticky='ew', padx=(0, 3))
        ttk.Button(io_frame, text="Import CSV", 
                  command=self._on_import).grid(row=0, column=1, sticky='ew', padx=(3, 0))
        
        # ===== Scenario Selection =====
        scenario_frame = ttk.LabelFrame(parent, text="Scenario", padding=10)
        scenario_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        scenario_frame.columnconfigure(0, weight=1)
        row += 1
        
        ttk.Label(scenario_frame, text="Select Scenario:").grid(row=0, column=0, sticky='w')
        self.scenario_combo = ttk.Combobox(scenario_frame, state='readonly', width=30)
        self.scenario_combo.grid(row=1, column=0, sticky='ew', pady=(3, 0))
        self.scenario_combo.bind('<<ComboboxSelected>>', self._on_scenario_selected)
        
        # ===== Playback Controls =====
        play_frame = ttk.LabelFrame(parent, text="Playback", padding=10)
        play_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        play_frame.columnconfigure(0, weight=1)
        row += 1
        
        # Frame info
        self.frame_label = ttk.Label(play_frame, text="Frame: 0 / 0", font=('Arial', 11, 'bold'))
        self.frame_label.grid(row=0, column=0, pady=(0, 5))
        
        # Frame slider
        self.frame_slider = ttk.Scale(play_frame, from_=0, to=100, 
                                      orient=tk.HORIZONTAL,
                                      command=self._on_frame_slider)
        self.frame_slider.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        
        # Playback buttons frame
        btn_frame = ttk.Frame(play_frame)
        btn_frame.grid(row=2, column=0, sticky='ew')
        btn_frame.columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        ttk.Button(btn_frame, text="|<", width=5, 
                  command=self._on_first_frame).grid(row=0, column=0, padx=2)
        ttk.Button(btn_frame, text="<<", width=5, 
                  command=self._on_prev_frame).grid(row=0, column=1, padx=2)
        self.play_btn = ttk.Button(btn_frame, text=">", width=5, 
                                   command=self._on_play_pause)
        self.play_btn.grid(row=0, column=2, padx=2)
        ttk.Button(btn_frame, text=">>", width=5, 
                  command=self._on_next_frame).grid(row=0, column=3, padx=2)
        ttk.Button(btn_frame, text=">|", width=5, 
                  command=self._on_last_frame).grid(row=0, column=4, padx=2)
        
        # Speed control
        speed_frame = ttk.Frame(play_frame)
        speed_frame.grid(row=3, column=0, sticky='ew', pady=(10, 0))
        speed_frame.columnconfigure(1, weight=1)
        
        ttk.Label(speed_frame, text="Speed:").grid(row=0, column=0, sticky='w')
        self.speed_combo = ttk.Combobox(speed_frame, values=['0.25x', '0.5x', '1x', '2x', '4x'],
                                        state='readonly', width=10)
        self.speed_combo.set('1x')
        self.speed_combo.grid(row=0, column=1, sticky='e')
        self.speed_combo.bind('<<ComboboxSelected>>', self._on_speed_change)
        
        # ===== Algorithm Section =====
        algo_frame = ttk.LabelFrame(parent, text="Algorithm", padding=10)
        algo_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        algo_frame.columnconfigure(0, weight=1)
        row += 1
        
        ttk.Button(algo_frame, text="Run Prediction", 
                  command=self._on_run_prediction, style='Big.TButton').grid(row=0, column=0, sticky='ew', pady=2)
        ttk.Button(algo_frame, text="Run Evaluation", 
                  command=self._on_run_evaluation).grid(row=1, column=0, sticky='ew', pady=2)
        ttk.Button(algo_frame, text="Show Report", 
                  command=self._on_show_report).grid(row=2, column=0, sticky='ew', pady=2)
        
        # ===== Threshold Settings =====
        thresh_frame = ttk.LabelFrame(parent, text="Thresholds", padding=10)
        thresh_frame.grid(row=row, column=0, sticky='ew', pady=(0, 10))
        thresh_frame.columnconfigure(1, weight=1)
        row += 1
        
        # TTC threshold
        ttk.Label(thresh_frame, text="TTC (s):").grid(row=0, column=0, sticky='w', pady=3)
        self.ttc_thresh_var = tk.StringVar(value="1.0")
        ttk.Entry(thresh_frame, textvariable=self.ttc_thresh_var, width=12).grid(
            row=0, column=1, sticky='e', pady=3, padx=(10, 0))
        
        # DRAC threshold
        ttk.Label(thresh_frame, text="DRAC (m/s²):").grid(row=1, column=0, sticky='w', pady=3)
        self.drac_thresh_var = tk.StringVar(value="6.0")
        ttk.Entry(thresh_frame, textvariable=self.drac_thresh_var, width=12).grid(
            row=1, column=1, sticky='e', pady=3, padx=(10, 0))
        
        ttk.Button(thresh_frame, text="Apply", 
                  command=self._on_apply_thresholds).grid(row=2, column=0, columnspan=2, sticky='ew', pady=(10, 0))
        
    def _build_visualization_panel(self, parent: ttk.Frame):
        """Build the BEV visualization panel."""
        # Title
        title = ttk.Label(parent, text="Bird's Eye View", font=('Arial', 12, 'bold'))
        title.grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        # Create visualizer
        self.visualizer = BEVVisualizer(self.vis_config, self.sim_config)
        
        # Create canvas
        self.canvas = self.visualizer.create_canvas(parent)
        self.canvas.grid(row=1, column=0, sticky='nsew')
        
        # Draw initial empty state
        self.visualizer.draw_road()
        
    def _build_info_panel(self, parent: ttk.Frame):
        """Build the information panel on the right."""
        # Create info panel widget
        self.info_panel = InfoPanel(parent)
        
    def _update_scenario_list(self):
        """Update the scenario selection dropdown."""
        if self.current_dataset is None:
            self.scenario_combo['values'] = []
            return
        
        scenario_ids = sorted(self.current_dataset.keys())
        self.scenario_combo['values'] = [f"Scenario {sid}" for sid in scenario_ids]
        
        if scenario_ids:
            self.scenario_combo.current(0)
            self._on_scenario_selected(None)
    
    def _update_frame_display(self):
        """Update the frame display."""
        if self.current_dataset is None or self.current_scenario_id is None:
            return
        
        frames = self.current_dataset.get(self.current_scenario_id, [])
        if not frames or self.current_frame_idx >= len(frames):
            return
        
        frame = frames[self.current_frame_idx]
        
        # Get predictions for this frame
        frame_predictions = []
        if self.current_predictions is not None:
            scenario_pred = self.current_predictions.get(self.current_scenario_id)
            if scenario_pred:
                frame_predictions = [
                    p for p in scenario_pred.predictions 
                    if p.frame_id == self.current_frame_idx
                ]
        
        # Draw frame
        self.visualizer.draw_frame(frame, frame_predictions)
        
        # Update info panel
        self.info_panel.update(frame_predictions)
        
        # Update frame label
        self.frame_label.config(text=f"Frame: {self.current_frame_idx + 1} / {len(frames)}")
    
    # ===== Event Handlers =====
    
    def _on_generate(self):
        """Handle generate button click."""
        try:
            num_scenarios = int(self.num_scenarios_var.get())
            seed = int(self.seed_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid number of scenarios or seed")
            return
        
        # Generate data
        self.data_generator.set_seed(seed)
        self.current_dataset = self.data_generator.generate_dataset(num_scenarios, seed)
        self.current_predictions = None
        self.evaluation_results = None
        
        # Update UI
        self._update_scenario_list()
        
        messagebox.showinfo("Success", f"Generated {num_scenarios} scenarios")
    
    def _on_create_custom(self):
        """Handle create custom scenario button."""
        import tkinter.simpledialog
        
        # Make simpledialog available for the editor
        import tkinter as tk
        tk.simpledialog = __import__('tkinter.simpledialog', fromlist=['simpledialog'])
        
        dialog = ScenarioEditorDialog(self.root)
        frames = dialog.show()
        
        if frames:
            # Create new scenario ID
            if self.current_dataset is None:
                self.current_dataset = {}
                
            # Find next scenario ID
            existing_ids = set(self.current_dataset.keys()) if self.current_dataset else set()
            new_id = 0
            while new_id in existing_ids:
                new_id += 1
                
            self.current_dataset[new_id] = frames
            self.current_predictions = None
            self.evaluation_results = None
            
            self._update_scenario_list()
            
            # Select the new scenario
            self.scenario_combo.set(f"Scenario {new_id}")
            self._on_scenario_selected(None)
            
            messagebox.showinfo("Success", f"Custom scenario {new_id} created with {len(frames)} frames.")
    
    def _on_edit_scenario(self):
        """Edit the current scenario."""
        import tkinter.simpledialog
        import tkinter as tk
        tk.simpledialog = __import__('tkinter.simpledialog', fromlist=['simpledialog'])
        
        if self.current_dataset is None or self.current_scenario_id is None:
            messagebox.showerror("Error", "No scenario selected.\nGenerate or import data first.")
            return
        
        # Get current scenario frames
        current_frames = self.current_dataset.get(self.current_scenario_id, [])
        if not current_frames:
            messagebox.showerror("Error", "No frames in current scenario.")
            return
            
        # Open editor with current frames
        dialog = ScenarioEditorDialog(self.root, {self.current_scenario_id: current_frames})
        frames = dialog.show()
        
        if frames:
            self.current_dataset[self.current_scenario_id] = frames
            self.current_predictions = None
            self.evaluation_results = None
            self.current_frame_idx = 0
            
            self._update_frame_display()
            
            messagebox.showinfo("Success", f"Scenario {self.current_scenario_id} updated with {len(frames)} frames.")
    
    def _on_export(self):
        """Handle export button click."""
        if self.current_dataset is None:
            messagebox.showerror("Error", "No data to export.\nGenerate or import data first.")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.data_loader.base_dir
        )
        
        if filename:
            self.data_loader.export_to_csv(self.current_dataset, filename)
            messagebox.showinfo("Success", f"Data exported to:\n{filename}")
    
    def _on_import(self):
        """Handle import button click."""
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            initialdir=self.data_loader.base_dir
        )
        
        if filename:
            try:
                self.current_dataset = self.data_loader.import_from_csv(filename)
                self.current_predictions = None
                self.evaluation_results = None
                self._update_scenario_list()
                messagebox.showinfo("Success", f"Imported {len(self.current_dataset)} scenarios")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import:\n{str(e)}")
    
    def _on_scenario_selected(self, event):
        """Handle scenario selection."""
        selection = self.scenario_combo.get()
        if selection:
            try:
                self.current_scenario_id = int(selection.split()[-1])
            except:
                return
            
            self.current_frame_idx = 0
            
            frames = self.current_dataset.get(self.current_scenario_id, [])
            self.frame_slider.config(to=max(0, len(frames) - 1))
            self.frame_slider.set(0)
            
            self._update_frame_display()
    
    def _on_frame_slider(self, value):
        """Handle frame slider change."""
        self.current_frame_idx = int(float(value))
        self._update_frame_display()
    
    def _on_first_frame(self):
        """Go to first frame."""
        self.current_frame_idx = 0
        self.frame_slider.set(0)
        self._update_frame_display()
    
    def _on_prev_frame(self):
        """Go to previous frame."""
        if self.current_frame_idx > 0:
            self.current_frame_idx -= 1
            self.frame_slider.set(self.current_frame_idx)
            self._update_frame_display()
    
    def _on_next_frame(self):
        """Go to next frame."""
        if self.current_dataset is None or self.current_scenario_id is None:
            return
        
        frames = self.current_dataset.get(self.current_scenario_id, [])
        if self.current_frame_idx < len(frames) - 1:
            self.current_frame_idx += 1
            self.frame_slider.set(self.current_frame_idx)
            self._update_frame_display()
    
    def _on_last_frame(self):
        """Go to last frame."""
        if self.current_dataset is None or self.current_scenario_id is None:
            return
        
        frames = self.current_dataset.get(self.current_scenario_id, [])
        self.current_frame_idx = len(frames) - 1
        self.frame_slider.set(self.current_frame_idx)
        self._update_frame_display()
    
    def _on_play_pause(self):
        """Toggle playback."""
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.play_btn.config(text="||")
            self._play_animation()
        else:
            self.play_btn.config(text=">")
    
    def _play_animation(self):
        """Play animation loop."""
        if not self.is_playing:
            return
        
        if self.current_dataset is None or self.current_scenario_id is None:
            self.is_playing = False
            self.play_btn.config(text=">")
            return
        
        frames = self.current_dataset.get(self.current_scenario_id, [])
        
        if self.current_frame_idx < len(frames) - 1:
            self.current_frame_idx += 1
            self.frame_slider.set(self.current_frame_idx)
            self._update_frame_display()
            
            delay = int(100 / self.playback_speed)
            self.root.after(delay, self._play_animation)
        else:
            self.is_playing = False
            self.play_btn.config(text=">")
    
    def _on_speed_change(self, event):
        """Handle speed change."""
        speed_str = self.speed_combo.get()
        self.playback_speed = float(speed_str.replace('x', ''))
    
    def _on_run_prediction(self):
        """Run prediction on current dataset."""
        if self.current_dataset is None:
            messagebox.showerror("Error", "No data loaded.\nGenerate or import data first.")
            return
        
        self.current_predictions = self.predictor.predict_dataset(self.current_dataset)
        self._update_frame_display()
        
        nm_count = sum(1 for p in self.current_predictions.values() if p.near_miss_detected)
        messagebox.showinfo("Prediction Complete", 
                          f"Processed {len(self.current_predictions)} scenarios\n"
                          f"Near-misses detected: {nm_count}")
    
    def _on_run_evaluation(self):
        """Run evaluation on predictions."""
        if self.current_predictions is None:
            messagebox.showerror("Error", "No predictions available.\nRun prediction first.")
            return
        
        self.evaluation_results = self.evaluator.evaluate_dataset(
            self.current_predictions, self.current_dataset
        )
        
        json_path, report_path = self.evaluator.save_results(self.evaluation_results)
        
        messagebox.showinfo("Evaluation Complete", 
                          f"Results saved to:\n{json_path}\n{report_path}")
    
    def _on_show_report(self):
        """Show evaluation report in a new window."""
        if self.evaluation_results is None:
            messagebox.showerror("Error", "No evaluation results.\nRun evaluation first.")
            return
        
        report_window = tk.Toplevel(self.root)
        report_window.title("Evaluation Report")
        report_window.geometry("750x650")
        
        text_frame = ttk.Frame(report_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget = tk.Text(text_frame, wrap=tk.NONE, font=('Courier', 11))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        text_widget.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=text_widget.yview)
        
        report = self.evaluator.generate_report(self.evaluation_results)
        text_widget.insert('1.0', report)
        text_widget.config(state=tk.DISABLED)
    
    def _on_apply_thresholds(self):
        """Apply new threshold settings."""
        try:
            ttc_thresh = float(self.ttc_thresh_var.get())
            drac_thresh = float(self.drac_thresh_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid threshold values")
            return
        
        self.predictor.near_miss_ttc_threshold = ttc_thresh
        self.predictor.near_miss_drac_threshold = drac_thresh
        
        messagebox.showinfo("Success", "Thresholds updated successfully")


def main():
    """Main entry point."""
    root = tk.Tk()
    app = SimulatorApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
