"""
Data loader for CSV import/export of synthetic tracking data.
"""

import csv
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

from .scenario_types import TrackedObject, EgoVehicle, FrameData


class DataLoader:
    """Handles import/export of tracking data to/from CSV files."""
    
    CSV_COLUMNS = [
        'scenario_id', 'frame_id', 'timestamp', 'object_id', 'object_class',
        'x', 'y', 'vx', 'vy', 'length', 'width', 'heading',
        'ego_vx', 'ego_vy', 'ground_truth_label', 'conflict_type', 'ttc'
    ]
    
    def __init__(self, base_dir: str = None):
        """Initialize data loader with base directory for datasets."""
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Dataset')
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
    
    def export_to_csv(self, dataset: Dict[int, List[FrameData]], 
                      filename: str, 
                      include_metadata: bool = True) -> str:
        """Export dataset to CSV file.
        
        Args:
            dataset: Dictionary mapping scenario_id to list of FrameData
            filename: Output filename (will be placed in base_dir if not absolute)
            include_metadata: Whether to include metadata JSON alongside CSV
            
        Returns:
            Path to the created CSV file
        """
        if not os.path.isabs(filename):
            filename = os.path.join(self.base_dir, filename)
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.CSV_COLUMNS)
            writer.writeheader()
            
            for scenario_id, frames in dataset.items():
                for frame in frames:
                    for obj in frame.objects:
                        
                        # Find if this object has a corresponding ground truth event
                        gt_label = 'None'
                        conflict_type = 'None'
                        ttc_val = 'None'
                        
                        if frame.ground_truth_events:
                            for event in frame.ground_truth_events:
                                # Events should have object_id to link to specific objects
                                if event.get('object_id') == obj.object_id:
                                    gt_label = event.get('type', 'None')
                                    # Handle case where type is near_miss but stored differently
                                    if gt_label == 'near_miss':
                                        conflict_type = event.get('scenario_type', 'None')
                                        ttc_val = event.get('ttc', 'None')
                                    break

                        row = {
                            'scenario_id': scenario_id,
                            'frame_id': frame.frame_id,
                            'timestamp': frame.timestamp,
                            'object_id': obj.object_id,
                            'object_class': obj.object_class,
                            'x': obj.x,
                            'y': obj.y,
                            'vx': obj.vx,
                            'vy': obj.vy,
                            'length': obj.length,
                            'width': obj.width,
                            'heading': obj.heading,
                            'ego_vx': frame.ego.vx,
                            'ego_vy': frame.ego.vy,
                            'ground_truth_label': gt_label,
                            'conflict_type': conflict_type,
                            'ttc': str(ttc_val)
                        }
                        writer.writerow(row)
        
        if include_metadata:
            self._write_metadata(filename, dataset)
        
        return filename
    
    def _write_metadata(self, csv_path: str, dataset: Dict[int, List[FrameData]]):
        """Write metadata JSON file alongside CSV."""
        metadata_path = csv_path.replace('.csv', '_metadata.json')
        
        metadata = {
            'created_at': datetime.now().isoformat(),
            'num_scenarios': len(dataset),
            'total_frames': sum(len(frames) for frames in dataset.values()),
            'total_objects': sum(
                sum(len(f.objects) for f in frames) 
                for frames in dataset.values()
            ),
            'scenarios': {}
        }
        
        for scenario_id, frames in dataset.items():
            scenario_meta = {
                'num_frames': len(frames),
                'duration': frames[-1].timestamp if frames else 0,
                'num_objects': len(set(obj.object_id for f in frames for obj in f.objects)),
                'has_near_miss': any(f.ground_truth_events for f in frames)
            }
            metadata['scenarios'][str(scenario_id)] = scenario_meta
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def import_from_csv(self, filename: str) -> Dict[int, List[FrameData]]:
        """Import dataset from CSV file.
        
        Args:
            filename: Path to CSV file (relative to base_dir or absolute)
            
        Returns:
            Dictionary mapping scenario_id to list of FrameData
        """
        if not os.path.isabs(filename):
            filename = os.path.join(self.base_dir, filename)
        
        if not os.path.exists(filename):
            raise FileNotFoundError(f"Dataset file not found: {filename}")
        
        # Read all rows
        rows_by_scenario_frame = {}
        
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                scenario_id = int(row['scenario_id'])
                frame_id = int(row['frame_id'])
                
                if scenario_id not in rows_by_scenario_frame:
                    rows_by_scenario_frame[scenario_id] = {}
                
                if frame_id not in rows_by_scenario_frame[scenario_id]:
                    rows_by_scenario_frame[scenario_id][frame_id] = {
                        'timestamp': float(row['timestamp']),
                        'ego_vx': float(row['ego_vx']),
                        'ego_vy': float(row['ego_vy']),
                        'ground_truth_events': [],
                        'objects': []
                    }
                
                # Create tracked object
                obj_id = int(row['object_id'])
                obj = TrackedObject(
                    object_id=obj_id,
                    x=float(row['x']),
                    y=float(row['y']),
                    vx=float(row['vx']),
                    vy=float(row['vy']),
                    length=float(row['length']),
                    width=float(row['width']),
                    object_class=row['object_class'],
                    heading=float(row.get('heading', 0))
                )
                
                rows_by_scenario_frame[scenario_id][frame_id]['objects'].append(obj)
                
                # Reconstruct ground truth event from row columns
                gt_label = row.get('ground_truth_label', 'None')
                if gt_label != 'None' and gt_label != '':
                    
                    # Normalize 'check' values if any
                    conflict_type = row.get('conflict_type', 'None')
                    ttc_str = row.get('ttc', 'None')
                    
                    event = {
                        "type": gt_label,
                        "object_id": obj_id,
                        "scenario_type": conflict_type,
                        "time": float(row['timestamp'])
                    }
                    
                    if ttc_str != 'None' and ttc_str != '':
                        try:
                            event['ttc'] = float(ttc_str)
                        except ValueError:
                            pass
                            
                    rows_by_scenario_frame[scenario_id][frame_id]['ground_truth_events'].append(event)
        
        # Convert to FrameData structure
        dataset = {}
        
        for scenario_id, frames_dict in rows_by_scenario_frame.items():
            frames = []
            
            for frame_id in sorted(frames_dict.keys()):
                frame_info = frames_dict[frame_id]
                
                # Use reconstructed events
                gt_events = frame_info['ground_truth_events']
                
                ego = EgoVehicle(
                    vx=frame_info['ego_vx'],
                    vy=frame_info['ego_vy']
                )
                
                frame = FrameData(
                    frame_id=frame_id,
                    timestamp=frame_info['timestamp'],
                    ego=ego,
                    objects=frame_info['objects'],
                    ground_truth_events=gt_events
                )
                frames.append(frame)
            
            dataset[scenario_id] = frames
        
        return dataset
    
    def list_datasets(self) -> List[Dict]:
        """List all available datasets in the base directory."""
        datasets = []
        
        for filename in os.listdir(self.base_dir):
            if filename.endswith('.csv') and not filename.endswith('_metadata.json'):
                filepath = os.path.join(self.base_dir, filename)
                
                # Try to load metadata
                metadata_path = filepath.replace('.csv', '_metadata.json')
                metadata = {}
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                    except:
                        pass
                
                datasets.append({
                    'filename': filename,
                    'path': filepath,
                    'size_bytes': os.path.getsize(filepath),
                    'modified': datetime.fromtimestamp(os.path.getmtime(filepath)).isoformat(),
                    'metadata': metadata
                })
        
        return sorted(datasets, key=lambda x: x['modified'], reverse=True)
    
    def export_predictions_to_csv(self, predictions: List[Dict], 
                                  filename: str) -> str:
        """Export prediction results to CSV.
        
        Args:
            predictions: List of prediction dictionaries
            filename: Output filename
            
        Returns:
            Path to created file
        """
        if not os.path.isabs(filename):
            filename = os.path.join(self.base_dir, filename)
        
        if not predictions:
            return filename
        
        # Get all unique keys from predictions
        all_keys = set()
        for pred in predictions:
            all_keys.update(pred.keys())
        
        columns = sorted(list(all_keys))
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()
            
            for pred in predictions:
                row = {k: pred.get(k, '') for k in columns}
                writer.writerow(row)
        
        return filename
    
    def export_evaluation_results(self, results: Dict, filename: str) -> str:
        """Export evaluation results to JSON.
        
        Args:
            results: Evaluation results dictionary
            filename: Output filename
            
        Returns:
            Path to created file
        """
        results_dir = os.path.join(os.path.dirname(self.base_dir), 'Results')
        os.makedirs(results_dir, exist_ok=True)
        
        if not os.path.isabs(filename):
            filename = os.path.join(results_dir, filename)
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return filename
