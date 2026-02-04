# Near-Miss Simulator Documentation

## Algorithm Flowchart

### Option 1: View in Editor (Mermaid)
Open `near_miss_algorithm_flowchart.md` in VS Code or GitHub to see the diagrams rendered natively.

### Option 2: Generate High-Quality PNG (Graphviz)
To generate a standalone image file (`.png`), use the provided Python script.

**Prerequisites:**
1.  **System Library**: You must have Graphviz installed on your OS.
    *   **macOS**: `brew install graphviz`
    *   **Windows**: Download installer from [graphviz.org](https://graphviz.org/download/)
    *   **Linux**: `sudo apt-get install graphviz`
2.  **Python Library**: Install the wrapper.
    ```bash
    pip install graphviz
    ```

**Generation:**
Run the script from the project root:
```bash
python Code/Simulator/Documentations/generate_flowchart.py
```
This will output `near_miss_algorithm_flowchart.png`.
