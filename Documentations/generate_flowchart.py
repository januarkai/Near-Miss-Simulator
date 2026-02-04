
try:
    from graphviz import Digraph
except ImportError:
    print("Error: 'graphviz' python library is not installed.")
    print("Please install it running: pip install graphviz")
    print("Note: You also need the Graphviz system binary installed.")
    print("      MacOS: brew install graphviz")
    print("      Ubuntu: sudo apt-get install graphviz")
    print("      Windows: Download installer from graphviz.org")
    exit(1)

def generate_flowchart():
    dot = Digraph('NearMissPrediction', comment='Deterministic Near-Miss Prediction Logic', format='png')
    
    # Graph Attributes
    dot.attr(rankdir='TB', size='10,10', bgcolor='white')
    dot.attr('node', shape='box', style='filled', fillcolor='lightblue', fontname='Helvetica', fontsize='12')
    dot.attr('edge', fontname='Helvetica', fontsize='10')

    # Nodes
    dot.node('Start', 'Start: Receive Frame Data', shape='ellipse', fillcolor='lightgreen')
    
    # Object Loop
    dot.node('ObjLoop', 'Iterate Objects\n(Relative to Ego)', shape='diamond', fillcolor='orange')
    
    # 1. SSM Calculation
    dot.node('SSM', 'Calculate SSMs\n(TTC, DRAC, MDR)', shape='box')
    
    # 2. Conflict Detection
    dot.node('ConflictDetect', 'Detect Conflict Type\n(Pos & Velocity Check)', shape='box')
    dot.node('ConflictCheck', 'Conflict Detected?', shape='diamond', fillcolor='orange')
    
    # 3. Trajectory
    dot.node('TrajPred', 'Predict Trajectory\n(Constant Velocity Model)', shape='box')
    dot.node('ColCheck', 'Predict Collision Point', shape='box')
    
    # 4. Classification Logic
    dot.node('TTC_Check', 'TTC < Threshold\n(e.g., < 2.0s)', shape='diamond', fillcolor='lightyellow')
    dot.node('DRAC_Check', 'DRAC > Threshold\n(e.g., > 3.0 m/s²)', shape='diamond', fillcolor='lightyellow')
    dot.node('MDR_Check', 'MDR < Threshold\n(e.g., < 1.0)', shape='diamond', fillcolor='lightyellow')
    
    dot.node('MultiCriteria', 'Count Critical Criteria\n(Conflict + SSMs)', shape='box')
    dot.node('IsCritical', 'Is Critical?\n(>= 2 flags OR \nHigh Risk)', shape='diamond', fillcolor='orange')
    
    # Outcomes
    dot.node('NearMiss', 'Classify: NEAR-MISS\n(High Risk)', shape='box', fillcolor='red', fontcolor='white')
    dot.node('Warning', 'Classify: WARNING\n(Moderate Risk)', shape='box', fillcolor='yellow')
    dot.node('Safe', 'Classify: SAFE', shape='box', fillcolor='lightgrey')
    
    dot.node('Confidence', 'Calculate ConfidenceScore', shape='box')
    dot.node('Output', 'Output PredictionResult', shape='parallelogram', fillcolor='lightgreen')

    # Edges
    dot.edge('Start', 'ObjLoop')
    dot.edge('ObjLoop', 'SSM', label='Next Object')
    
    dot.edge('SSM', 'ConflictDetect')
    dot.edge('ConflictDetect', 'ConflictCheck')
    
    dot.edge('ConflictCheck', 'TrajPred', label='Yes/No')
    dot.edge('TrajPred', 'ColCheck')
    
    dot.edge('ColCheck', 'TTC_Check')
    
    # Logic Flow
    dot.edge('TTC_Check', 'DRAC_Check')
    dot.edge('DRAC_Check', 'MDR_Check')
    dot.edge('MDR_Check', 'MultiCriteria')
    
    # Connecting Conflict result to criteria count
    dot.edge('ConflictCheck', 'MultiCriteria', label='Input')
    
    dot.edge('MultiCriteria', 'IsCritical')
    
    dot.edge('IsCritical', 'NearMiss', label='Yes')
    dot.edge('IsCritical', 'Warning', label='Moderate')
    dot.edge('IsCritical', 'Safe', label='No')
    
    dot.edge('NearMiss', 'Confidence')
    dot.edge('Warning', 'Confidence')
    dot.edge('Safe', 'Confidence')
    
    dot.edge('Confidence', 'Output')
    dot.edge('Output', 'ObjLoop', label='Next')

    # Save
    output_path = 'Code/Simulator/Documentations/near_miss_algorithm_flowchart'
    dot.render(output_path, view=False)
    print(f"Flowchart generated successfully: {output_path}.png")

if __name__ == '__main__':
    generate_flowchart()
