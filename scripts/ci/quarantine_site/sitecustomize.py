"""
Activates the CardioVanta data quarantine in every Python process started with this directory on
PYTHONPATH and CARDIOVANTA_DATA_QUARANTINE=1 (including subprocesses that inherit the environment).
"""
import os

if os.environ.get("CARDIOVANTA_DATA_QUARANTINE") == "1":
    import importlib.util as _ilu
    from pathlib import Path as _Path

    _spec = _ilu.spec_from_file_location("cardiovanta_data_quarantine", _Path(__file__).resolve().parents[1] / "data_quarantine.py")
    _mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.install()
