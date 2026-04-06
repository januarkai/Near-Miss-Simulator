import json, os

results_dir = '/Users/januarkailanisuaeb/Documents/Personal/Kuliah/Tesis/Code/Simulator/Results'
files = sorted([f for f in os.listdir(results_dir) if f.endswith('.json') and f.startswith('evaluation_')])[-3:]
for f in files:
    d = json.load(open(os.path.join(results_dir, f)))
    algo = d.get('algorithm_name', '?')
    cm = d.get('confusion_matrix', {})
    print(f'[{algo}]')
    tp = cm.get('true_positives', 0)
    tn = cm.get('true_negatives', 0)
    fp = cm.get('false_positives', 0)
    fn = cm.get('false_negatives', 0)
    print(f'  TP/TN/FP/FN: {tp}/{tn}/{fp}/{fn}')
    print(f'  Accuracy:       {cm.get("accuracy", 0):.4f}')
    print(f'  Precision:      {cm.get("precision", 0):.4f}')
    print(f'  Recall:         {cm.get("recall", 0):.4f}')
    print(f'  F1 Score:       {cm.get("f1_score", 0):.4f}')
    print(f'  FPR:            {cm.get("false_positive_rate", 0):.4f}')
    print(f'  Type Accuracy:  {d.get("type_accuracy_global", 0):.4f}')
    print(f'  Brier Score:    {d.get("brier_score", 0):.4f}')
    print(f'  AUROC:          {d.get("auroc", 0):.4f}')
    print(f'  Mean t-IoU:     {d.get("mean_tiou", 0):.4f}')
    print()
