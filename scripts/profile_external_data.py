"""
CardioVanta External Data Acquisition and Profiling CLI (Phase 17 Task 1.1)
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cardiovanta.data.external_loader import (
    download_external_datasets,
    profile_raw_cohort,
    generate_multicenter_profiling_report,
)

def main():
    external_raw_dir = PROJECT_ROOT / "data" / "external" / "raw"
    reports_dir = PROJECT_ROOT / "reports"
    
    print(f"Acquiring and verifying raw external datasets into {external_raw_dir}...")
    files = download_external_datasets(external_raw_dir)
    for k, v in files.items():
        print(f"  [OK] {k} -> {v}")

    print("\nProfiling raw cohorts...")
    p_hungary = profile_raw_cohort(files["hungarian.data"], "Hungarian Cohort (Budapest)")
    p_va = profile_raw_cohort(files["long-beach-va.data"], "Long Beach VA Cohort (California)")
    
    md_path = reports_dir / "external_data_profiling.md"
    json_path = reports_dir / "external_data_profiling.json"
    
    print(f"Generating profiling report at {md_path} and {json_path}...")
    generate_multicenter_profiling_report([p_hungary, p_va], md_path, json_path)
    print("Report generated successfully.")

if __name__ == "__main__":
    main()
