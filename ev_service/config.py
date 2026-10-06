"""Configuration constants for the local EV microgrid demo."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"
POLICY_FILE = DATA_DIR / "policies.json"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

DEMO_SEED = 42
DEMO_DATE = "2026-01-01"
MODEL_VERSION = "ev-microgrid-demo-0.1"
DEFAULT_HORIZON_HOURS = 24
DEFAULT_FLEET_SIZE = 8
DEFAULT_RESERVE_SOC = 0.20
DEFAULT_RENEWABLE_TARGET = 0.55
