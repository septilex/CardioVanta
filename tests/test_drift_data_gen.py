import json
import logging
from typing import List, Dict, Any
from src.config.config import BASE_DIR, RAW_DATA_PATH, load_schema

def generate_synthetic_logs(
    output_path: str,
    num_events: int,
    drift_type: str = "none",
    boundary_violation_rate: float = 0.0,
    constant_prob: float = None,
    package_version: str = "1.0.0",
    model_type: str = "Logistic Regression"
):
    """
    Generates synthetic JSON logs matching Phase 15A telemetry.
    drift_type: "none", "clear", "borderline"
    """
    import numpy as np
    np.random.seed(42)
    
    logs = []
    for i in range(num_events):
        
        # Base probabilities
        if constant_prob is not None:
            prob = constant_prob
        elif drift_type == "none":
            prob = np.random.uniform(0.1, 0.9)
        elif drift_type == "clear":
            prob = np.random.uniform(0.6, 0.99) # Shifted high
        elif drift_type == "borderline":
            prob = np.random.uniform(0.2, 0.9) # Slightly shifted
        else:
            prob = np.random.uniform(0.1, 0.9)
            
        is_out_of_range = np.random.random() < boundary_violation_rate
        
        event = {
            "event_type": "prediction_event",
            "request_id": f"req_{i}",
            "endpoint": "/api/v1/predict",
            "package_version": package_version,
            "model_type": model_type,
            "calibration_method": "sigmoid",
            "status_code": 200,
            "latency_ms": 15.5,
            "prediction_probability": prob,
            "threshold_status": "no_validated_production_threshold_configured",
            "outside_development_range": bool(is_out_of_range),
            "out_of_range_features": ["age"] if is_out_of_range else []
        }
        logs.append(event)
        
    # Write to file as jsonlines
    with open(output_path, "w") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")
            
    return logs
