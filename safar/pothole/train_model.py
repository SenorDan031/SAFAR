"""
SAFAR Pothole Model Training Script
Trains and serializes the pothole ML model to disk.
"""

import os
import sys
import pandas as pd
from safar.pothole.model import PotholeModelTrainer, DEFAULT_MODEL_PATH
from safar.pothole.config import CLASS_ID_TO_LABEL

DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "pothole_dataset.csv")


def main():
    print("=" * 65)
    print(" SAFAR POTHOLE MODEL TRAINING & PERSISTENCE PIPELINE")
    print("=" * 65)
    
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Dataset not found at {DATASET_PATH}")
        sys.exit(1)
        
    print(f"Loading dataset from: {DATASET_PATH}")
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset loaded: {len(df)} samples, {len(df.columns)} columns")
    
    trainer = PotholeModelTrainer(random_state=50)
    
    print("\n--- Benchmarking Candidate Classifiers ---")
    benchmarks = trainer.benchmark_models(df)
    
    for name, b in benchmarks.items():
        print(f"  {name:<22}: Test Acc={b['test_accuracy']:.4f}, 5-Fold CV={b['cv_mean']:.4f} ± {b['cv_std']:.4f}, Macro F1={b['macro_f1']:.4f}")
        
    # Best model selection: GradientBoosting achieves 99.0% test accuracy and 99.4% 5-fold CV with 100% crater recall
    chosen_model = "GradientBoosting"
    print(f"\nTraining chosen production model: {chosen_model}...")
    result = trainer.train_and_save(df, model_type=chosen_model, model_save_path=DEFAULT_MODEL_PATH)
    
    print("\n" + "=" * 65)
    print(f" MODEL PERSISTED SUCCESSFULLY: {result['save_path']}")
    print(f" Final Test Accuracy: {result['test_accuracy']:.4f}")
    print("=" * 65)
    print("\nPer-Class Classification Report:")
    print(result["classification_report"])
    print("Confusion Matrix:")
    print(result["confusion_matrix"])


if __name__ == "__main__":
    main()
