import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support

DATASET_PATH = r"C:\Users\shrey\OneDrive\Desktop\Projects\SAFAR\data\pothole_dataset.csv"

def run_model_comparison():
    print("=" * 70)
    print(" SAFAR POTHOLE MODEL COMPARISON & BENCHMARK")
    print("=" * 70)
    
    df = pd.read_csv(DATASET_PATH)
    feature_cols = ["PH_Width", "PH_Length", "PH_Depth"]
    target_col = "PH_Type"
    label_map = {0: "drivable_path", 1: "Sml_ph", 2: "Mid_ph", 3: "Crater"}
    
    X = df[feature_cols]
    y = df[target_col]
    
    # 1. Stratified Train/Test Split (80% Train, 20% Test, random_state=50)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=50, stratify=y
    )
    
    print(f"Total Dataset: {len(df)} samples")
    print(f"Training Set : {len(X_train)} samples")
    print(f"Test Set     : {len(X_test)} samples")
    print("\nClass distribution in Test Set:")
    for c in sorted(y.unique()):
        cnt = (y_test == c).sum()
        pct = (cnt / len(y_test)) * 100
        print(f"  Class {c} ({label_map[c]:14s}): {cnt:2d} samples ({pct:5.2f}%)")
        
    models = {
        "Decision Tree (Baseline)": DecisionTreeClassifier(random_state=50),
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=50),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, max_depth=3, random_state=50),
        "Extra Trees": ExtraTreesClassifier(n_estimators=100, max_depth=6, random_state=50)
    }
    
    results = {}
    
    for name, model in models.items():
        # Fit model
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        
        # Metrics
        acc = accuracy_score(y_test, y_pred)
        prec_macro, rec_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro", zero_division=0)
        prec_weighted, rec_weighted, f1_weighted, _ = precision_recall_fscore_support(y_test, y_pred, average="weighted", zero_division=0)
        
        # 5-fold Stratified Cross-Validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=50)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
        
        results[name] = {
            "model": model,
            "accuracy": acc,
            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted,
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "y_pred": y_pred,
            "cm": confusion_matrix(y_test, y_pred),
            "report": classification_report(y_test, y_pred, target_names=[label_map[i] for i in sorted(label_map.keys())], digits=4)
        }
        
    print("\n" + "=" * 70)
    print(" MODEL PERFORMANCE SUMMARY")
    print("=" * 70)
    print(f"{'Model Name':<28} | {'Test Acc':<9} | {'F1 (Macro)':<10} | {'F1 (Weight)':<11} | {'5-Fold CV Acc':<15}")
    print("-" * 75)
    for name, r in results.items():
        print(f"{name:<28} | {r['accuracy']:<9.4f} | {r['f1_macro']:<10.4f} | {r['f1_weighted']:<11.4f} | {r['cv_mean']:.4f} ± {r['cv_std']:.4f}")
        
    print("\n" + "=" * 70)
    print(" DETAILED PER-CLASS EVALUATION FOR EACH MODEL")
    print("=" * 70)
    
    for name, r in results.items():
        print(f"\n--- {name} ---")
        print(r["report"])
        print("Confusion Matrix:")
        print("                 Predicted: [drivable, Sml_ph, Mid_ph, Crater]")
        for idx, row in enumerate(r["cm"]):
            print(f"Actual {label_map[idx]:14s}: {row}")
            
    return results

if __name__ == "__main__":
    run_model_comparison()
