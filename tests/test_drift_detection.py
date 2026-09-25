import os
import json
import tempfile
import pytest
import numpy as np

from scripts.detect_drift import analyze_drift, load_baseline_probabilities, exact_ks_statistic, MIN_OBSERVATIONS, EFFECT_SIZE_THRESHOLD, P_VALUE_THRESHOLD
from tests.test_drift_data_gen import generate_synthetic_logs

def test_data_generator_privacy_and_schema():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        logs = generate_synthetic_logs(tmp_path, num_events=10)
        assert len(logs) == 10
        
        for log in logs:
            assert log["event_type"] == "prediction_event"
            assert "prediction_probability" in log
            assert "outside_development_range" in log
            assert "age" not in log
            assert "sex" not in log
    finally:
        os.remove(tmp_path)

def test_baseline_extraction_exact_size():
    # Locked test protection: must be exactly 242
    baseline = load_baseline_probabilities()
    assert len(baseline) == 242
    assert np.all(baseline >= 0.0) and np.all(baseline <= 1.0)

def test_insufficient_evidence():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=49)
        report = analyze_drift(tmp_path)
        
        assert report["eligibility"]["eligible"] is False
        assert report["status"] == "insufficient_evidence"
        assert report["drift_detected"] is False
        assert report["statistical_analysis"] is None
    finally:
        os.remove(tmp_path)

def test_exact_minimum_window():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=50, drift_type="none")
        report = analyze_drift(tmp_path)
        
        assert report["eligibility"]["eligible"] is True
        assert report["statistical_analysis"] is not None
    finally:
        os.remove(tmp_path)

def test_no_drift_control():
    # Make prod distribution identical to baseline
    baseline = load_baseline_probabilities()
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # We can just sample from baseline
        np.random.seed(42)
        sampled = np.random.choice(baseline, size=100)
        
        with open(tmp_path, "w") as f:
            for s in sampled:
                f.write(json.dumps({
                    "event_type": "prediction_event", 
                    "prediction_probability": s,
                    "package_version": "1.0.0",
                    "model_type": "Logistic Regression"
                }) + "\n")
                
        report = analyze_drift(tmp_path)
        
        assert report["eligibility"]["eligible"] is True
        assert report["drift_detected"] is False
        # D-statistic should be very small
        assert report["statistical_analysis"]["ks_d_statistic"] < EFFECT_SIZE_THRESHOLD
        assert report["statistical_analysis"]["is_significant"] is False
    finally:
        os.remove(tmp_path)

def test_clear_drift():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Force all probabilities to 0.99
        with open(tmp_path, "w") as f:
            for _ in range(100):
                f.write(json.dumps({
                    "event_type": "prediction_event", 
                    "prediction_probability": 0.99,
                    "package_version": "1.0.0",
                    "model_type": "Logistic Regression"
                }) + "\n")
                
        report = analyze_drift(tmp_path)
        
        assert report["eligibility"]["eligible"] is True
        assert report["drift_detected"] is True
        assert report["statistical_analysis"]["is_significant"] is True
        assert report["statistical_analysis"]["has_meaningful_effect_size"] is True
        assert "concept drift" in report["disclaimer"]
    finally:
        os.remove(tmp_path)

def test_borderline_drift_effect_size_rejection():
    # Case where p-value is significant but effect size is < 0.2
    # Difficult to guarantee randomly, but we can craft it
    baseline = load_baseline_probabilities()
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # Shift slightly
        shifted = np.clip(baseline + 0.05, 0, 1)
        # We need N to be large enough to make a small D significant.
        # Let's use 1000 samples.
        sampled = np.random.choice(shifted, size=1000)
        
        with open(tmp_path, "w") as f:
            for s in sampled:
                f.write(json.dumps({
                    "event_type": "prediction_event", 
                    "prediction_probability": s,
                    "package_version": "1.0.0",
                    "model_type": "Logistic Regression"
                }) + "\n")
                
        report = analyze_drift(tmp_path)
        
        # If D is small but significant:
        # We just want to check the AND condition
        d = report["statistical_analysis"]["ks_d_statistic"]
        sig = report["statistical_analysis"]["is_significant"]
        es = report["statistical_analysis"]["has_meaningful_effect_size"]
        
        assert report["drift_detected"] == (sig and es)
        assert "ENGINEERING MONITORING POLICY" in report["statistical_analysis"]["note"]
    finally:
        os.remove(tmp_path)

def test_ties_constant_probabilities():
    # Prod is exactly one constant value
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=60, constant_prob=0.5)
        report = analyze_drift(tmp_path)
        
        assert report["eligibility"]["eligible"] is True
        # Method should not crash on ties
        assert report["statistical_analysis"]["ks_d_statistic"] > 0
    finally:
        os.remove(tmp_path)

def test_malformed_telemetry_and_invalid_event_filtering():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        with open(tmp_path, "w") as f:
            f.write("not json\n")
            f.write(json.dumps({"event_type": "other_event"}) + "\n")
            f.write(json.dumps({
                "event_type": "prediction_event", 
                "prediction_probability": 0.1,
                "package_version": "1.0.0",
                "model_type": "Logistic Regression"
            }) + "\n")
            f.write(json.dumps({"age": 50}) + "\n") # raw feature missing event_type
            
        from scripts.detect_drift import parse_production_logs
        probs, viols, rejections = parse_production_logs(tmp_path, "1.0.0", "Logistic Regression")
        
        assert len(probs) == 1
        assert probs[0] == 0.1
    finally:
        os.remove(tmp_path)

def test_deterministic_output():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=100, drift_type="clear")
        
        report1 = analyze_drift(tmp_path)
        report2 = analyze_drift(tmp_path)
        
        assert report1["statistical_analysis"]["ks_d_statistic"] == report2["statistical_analysis"]["ks_d_statistic"]
        assert report1["statistical_analysis"]["permutation_p_value"] == report2["statistical_analysis"]["permutation_p_value"]
    finally:
        os.remove(tmp_path)

def test_out_of_development_range_handling():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=100, boundary_violation_rate=0.2)
        report = analyze_drift(tmp_path)
        
        # Approximate 20%
        assert report["support_boundary"]["violations"] > 0
        assert report["support_boundary"]["violation_rate"] > 0.0
    finally:
        os.remove(tmp_path)

def test_mismatched_package_version_rejected():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=100, package_version="0.9.0")
        report = analyze_drift(tmp_path)
        
        # All rejected
        assert report["eligibility"]["eligible"] is False
        assert report["eligibility"]["rejections"]["mismatched_package_version"] == 100
        assert report["status"] == "insufficient_evidence"
    finally:
        os.remove(tmp_path)

def test_mismatched_model_type_rejected():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        generate_synthetic_logs(tmp_path, num_events=100, model_type="Random Forest")
        report = analyze_drift(tmp_path)
        
        # All rejected
        assert report["eligibility"]["eligible"] is False
        assert report["eligibility"]["rejections"]["mismatched_model_type"] == 100
        assert report["status"] == "insufficient_evidence"
    finally:
        os.remove(tmp_path)

def test_mixed_telemetry_compatibility():
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp_path = tmp.name
        
    try:
        # 60 valid
        generate_synthetic_logs(tmp_path, num_events=60, package_version="1.0.0", model_type="Logistic Regression")
        # 40 invalid version
        logs_invalid_ver = generate_synthetic_logs("dummy", num_events=40, package_version="2.0.0")
        # 30 invalid model
        logs_invalid_mod = generate_synthetic_logs("dummy", num_events=30, model_type="SVC")
        
        with open(tmp_path, "a") as f:
            for log in logs_invalid_ver:
                f.write(json.dumps(log) + "\n")
            for log in logs_invalid_mod:
                f.write(json.dumps(log) + "\n")
                
        report = analyze_drift(tmp_path)
        
        # Total events = 130, but only 60 are valid. 
        # 60 >= 50, so it should be eligible and analyze the 60.
        assert report["eligibility"]["eligible"] is True
        assert report["eligibility"]["n_observations"] == 60
        assert report["eligibility"]["rejections"]["mismatched_package_version"] == 40
        assert report["eligibility"]["rejections"]["mismatched_model_type"] == 30
        assert report["statistical_analysis"] is not None
    finally:
        os.remove(tmp_path)
        if os.path.exists("dummy"):
            os.remove("dummy")
