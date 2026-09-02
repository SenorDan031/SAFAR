import sys
import os

try:
    import numpy as np
    import pandas as pd
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support
    import joblib
    print("SUCCESS: All ML libraries successfully imported!")
except Exception as e:
    print(f"Import Error: {e}")
    print("sys.executable:", sys.executable)
    print("sys.path:", sys.path)
