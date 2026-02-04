# Near-Miss Prediction Algorithm Flowchart

This flowchart describes the deterministic rule-based near-miss prediction logic implemented in the simulator.

```mermaid
flowchart TD
    %% Global Styles
    classDef process fill:#e1f5fe,stroke:#01579b,stroke-width:2px,color:black;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:black,shape:diamond;
    classDef terminator fill:#e0e0e0,stroke:#333,stroke-width:2px,color:black,shape:ellipse;
    classDef ssm fill:#e0f2f1,stroke:#00695c,stroke-width:1px,color:black;
    classDef outcome_nm fill:#ffcdd2,stroke:#c62828,stroke-width:3px,color:black;
    classDef outcome_safe fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px,color:black;

    Start([Start Scenario]):::terminator --> Init[Initialize Predictor & History]:::process
    Init --> LoopFrames{More Frames?}:::decision
    
    subgraph Frame_Processing [Process Frame t]
        direction TB
        LoopFrames -- Yes --> GetFrame[Get Frame t]:::process
        GetFrame --> UpdateModel[Update Trajectory Model]:::process
        UpdateModel --> IdentifyObjects[Identify Ego & Objects]:::process
        IdentifyObjects --> IterateObjects{Iterate Objects}:::decision
        
        subgraph Object_Analysis [Analyze Object i]
            direction TB
            IterateObjects -- Next Object --> GetState[Get State Pos, Vel]:::process
            GetState --> CalcSSM[Calculate SSMs]:::process
            
            %% SSM Detail
            CalcSSM --> CalcTTC(TTC):::ssm
            CalcSSM --> CalcDRAC(DRAC):::ssm
            CalcSSM --> CalcMDR(MDR):::ssm
            
            CalcTTC & CalcDRAC & CalcMDR --> DetectConflict[Detect Conflict Type]:::process
            DetectConflict -- Rear-End / Cut-In / Side-Swipe --> ConflictRes{Conflict?}:::decision
            
            ConflictRes --> PredictTraj[Linear Trajectory Prediction]:::process
            PredictTraj --> CheckCollision[Check Intersection]:::process
            
            CheckCollision --> RiskClass[Risk Classification]:::process
            
            RiskClass --> CheckThresholds{Check Thresholds}:::decision
            CheckThresholds -- "TTC < 2s OR DRAC > 4m/s²" --> Critical[Critical Violation]:::outcome_nm
            CheckThresholds -- "Normal Range" --> NonCritical[Safe Range]:::outcome_safe
            
            Critical --> CriteriaCount{Count Criteria}:::decision
            CriteriaCount -- ">= 2 Criteria OR (1 + Conflict)" --> NearMiss[Classify: NEAR MISS]:::outcome_nm
            CriteriaCount -- "Single Criteria" --> Warning[Classify: WARNING]:::decision
            NonCritical --> Safe[Classify: SAFE]:::outcome_safe
            
            NearMiss & Warning & Safe --> CalcConf[Calculate Confidence]:::process
        end
        
        CalcConf --> StoreRes[Store Result]:::process
        StoreRes --> IterateObjects
    end
    
    IterateObjects -- Done --> AggResults[Aggregate Frame Results]:::process
    AggResults --> LoopFrames
    
    LoopFrames -- No --> End([End Simulation]):::terminator
```

## Description of Logic

1.  **Initialization**: The predictor sets up tracking history and loads configuration/thresholds.
2.  **Frame Loop**: Iterates through each time step of the simulation.
3.  **Object Analysis**: For every object in the frame relative to the ego vehicle:
    *   **SSM Calculation**: Computes Surrogate Safety Measures like Time-To-Collision (TTC), Deceleration Rate to Avoid Collision (DRAC), and Minimum Distance Ratio (MDR).
    *   **Conflict Detection**: Analyzes spatial relationship (Ahead, Behind, Alongside) and velocity vectors to categorize conflict types (Rear-End, Side-Swipe, Cut-In, etc.).
    *   **Trajectory Prediction**: Uses a constant velocity model to project future positions (linear extrapolation).
4.  **Risk Classification**:
    *   Checks calculated SSMs against defined thresholds (Safe, Warning, Critical).
    *   A **Near-Miss** is declared if:
        *   TTC, DRAC, or MDR exceed critical thresholds.
        *   Multiple criteria are met simultaneously (e.g., Low TTC + Conflict Detected).
    *   **Confidence Score**: Calculated based on the consistency of the tracking history and agreement between multiple SSMs.
5.  **Result Aggregation**: Results are compiled for visualization and evaluation metrics.
