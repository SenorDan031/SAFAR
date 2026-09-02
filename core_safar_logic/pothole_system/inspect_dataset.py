import csv
import math
from collections import Counter, defaultdict

dataset_path = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\data\pothole_dataset.csv"

def inspect_dataset():
    rows = []
    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            rows.append(r)
            
    total_rows = len(rows)
    print("=" * 60)
    print(" SAFAR POTHOLE DATASET INSPECTION REPORT")
    print("=" * 60)
    print(f"Total Rows: {total_rows}")
    print(f"Columns: {fieldnames}")
    
    # Check nulls / empty strings
    null_counts = {k: 0 for k in fieldnames}
    type_counts = Counter()
    label_map = {}
    
    widths = []
    lengths = []
    depths = []
    
    class_stats = defaultdict(lambda: {"widths": [], "lengths": [], "depths": []})
    duplicates = 0
    seen_tuples = set()
    invalid_rows = 0
    
    for r in rows:
        row_tuple = tuple(r[k] for k in fieldnames)
        if row_tuple in seen_tuples:
            duplicates += 1
        seen_tuples.add(row_tuple)
        
        is_row_valid = True
        for k in fieldnames:
            if r[k] is None or r[k].strip() == "":
                null_counts[k] += 1
                is_row_valid = False
                
        try:
            w = float(r["PH_Width"])
            l = float(r["PH_Length"])
            d = float(r["PH_Depth"])
            ph_type = int(r["PH_Type"])
            ph_label = r["PH_Label"].strip()
            
            if w < 0 or l < 0 or d < 0:
                is_row_valid = False
                
            widths.append(w)
            lengths.append(l)
            depths.append(d)
            type_counts[ph_type] += 1
            label_map[ph_type] = ph_label
            
            class_stats[ph_type]["widths"].append(w)
            class_stats[ph_type]["lengths"].append(l)
            class_stats[ph_type]["depths"].append(d)
            
        except ValueError:
            is_row_valid = False
            
        if not is_row_valid:
            invalid_rows += 1
            
    print("\n--- Missing / Null Values per Column ---")
    for k, v in null_counts.items():
        print(f"  {k}: {v} missing")
        
    print(f"\n--- Duplicates: {duplicates} duplicate rows found ---")
    print(f"--- Invalid / Malformed Rows: {invalid_rows} ---")
    print(f"--- Valid Rows: {total_rows - invalid_rows} ({(total_rows - invalid_rows)/total_rows*100:.2f}%) ---")
    
    print("\n--- Class Distribution ---")
    for ph_type in sorted(type_counts.keys()):
        cnt = type_counts[ph_type]
        pct = (cnt / total_rows) * 100
        lbl = label_map.get(ph_type, "Unknown")
        print(f"  Class {ph_type} ({lbl:14s}): {cnt:4d} samples ({pct:5.2f}%)")
        
    def get_stats(arr):
        if not arr:
            return 0, 0, 0, 0
        mean = sum(arr) / len(arr)
        variance = sum((x - mean) ** 2 for x in arr) / len(arr)
        std = math.sqrt(variance)
        return min(arr), mean, max(arr), std
        
    print("\n--- Overall Feature Ranges (Meters) ---")
    w_min, w_mean, w_max, w_std = get_stats(widths)
    l_min, l_mean, l_max, l_std = get_stats(lengths)
    d_min, d_mean, d_max, d_std = get_stats(depths)
    print(f"  Width  : Min={w_min:.3f}m, Mean={w_mean:.3f}m, Max={w_max:.3f}m, Std={w_std:.3f}m")
    print(f"  Length : Min={l_min:.3f}m, Mean={l_mean:.3f}m, Max={l_max:.3f}m, Std={l_std:.3f}m")
    print(f"  Depth  : Min={d_min:.3f}m, Mean={d_mean:.3f}m, Max={d_max:.3f}m, Std={d_std:.3f}m")
    
    print("\n--- Per-Class Summary Statistics ---")
    for ph_type in sorted(class_stats.keys()):
        lbl = label_map.get(ph_type, "Unknown")
        c_w = class_stats[ph_type]["widths"]
        c_l = class_stats[ph_type]["lengths"]
        c_d = class_stats[ph_type]["depths"]
        
        w_min, w_mean, w_max, w_std = get_stats(c_w)
        l_min, l_mean, l_max, l_std = get_stats(c_l)
        d_min, d_mean, d_max, d_std = get_stats(c_d)
        
        print(f"\n  [Class {ph_type}: {lbl}] (n={len(c_w)})")
        print(f"    Width  : min={w_min:.3f}m, mean={w_mean:.3f}m, max={w_max:.3f}m, std={w_std:.3f}m")
        print(f"    Length : min={l_min:.3f}m, mean={l_mean:.3f}m, max={l_max:.3f}m, std={l_std:.3f}m")
        print(f"    Depth  : min={d_min:.3f}m, mean={d_mean:.3f}m, max={d_max:.3f}m, std={d_std:.3f}m")
        
    print("=" * 60)

if __name__ == "__main__":
    inspect_dataset()
