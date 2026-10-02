import json
import hashlib
import sys
from pathlib import Path

def calculate_sha256(filepath: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def verify_artifacts(manifest_path: str, base_dir: Path) -> bool:
    try:
        with open(manifest_path, "r") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"FAILED to load manifest from {manifest_path}: {e}")
        return False

    all_passed = True
    print("Verifying Artifact Integrity...")
    for rel_path, expected_hash in manifest.items():
        # Ensure cross-platform path handling
        full_path = base_dir / Path(rel_path)
        
        if not full_path.exists():
            print(f"[FAIL] Missing file: {rel_path}")
            all_passed = False
            continue
        
        try:
            actual_hash = calculate_sha256(full_path)
            if actual_hash == expected_hash:
                print(f"[PASS] {rel_path}")
            else:
                print(f"[FAIL] {rel_path}")
                print(f"       Expected: {expected_hash}")
                print(f"       Actual:   {actual_hash}")
                all_passed = False
        except Exception as e:
            print(f"[ERROR] Could not hash {rel_path}: {e}")
            all_passed = False
            
    return all_passed

if __name__ == "__main__":
    # We assume this script is run from the project root.
    base_dir = Path(__file__).parent.parent
    manifest_file = base_dir / "configs" / "artifact_hashes.json"
    
    if verify_artifacts(str(manifest_file), base_dir):
        print("All artifacts passed integrity check.")
        sys.exit(0)
    else:
        print("Artifact integrity check FAILED.")
        sys.exit(1)
