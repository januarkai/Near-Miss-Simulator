import json, glob, os

files = sorted(glob.glob('/Users/januarkailanisuaeb/Documents/Personal/Kuliah/Tesis/Code/Simulator/Results/evaluation_*.json'))[-2:]
for f in files:
    d = json.load(open(f))
    algo = d.get('algorithm_name', '?')
    correct = 0; total = 0; mismatches = {}
    for sid, sc in d.get('scenario_results', {}).items():
        for entry in sc.get('type_confusion_entries', []):
            gt_t, pred_t = entry
            total += 1
            if gt_t == pred_t:
                correct += 1
            else:
                key = f'{gt_t} -> {pred_t}'
                mismatches[key] = mismatches.get(key, 0) + 1
    acc = correct / total if total else 0
    print(f'[{algo}] {os.path.basename(f)}')
    print(f'  type accuracy: {correct}/{total} = {acc:.3f}')
    for k, v in sorted(mismatches.items(), key=lambda x: -x[1]):
        print(f'  WRONG: {k} (x{v})')
    print()
