"""Deterministic EV energy microgrid intelligence demo.

The package intentionally keeps all inputs local and synthetic.  It is useful for
demonstrations, API integration tests, and UI prototyping; it is not a production
charging controller.
"""

__version__ = "0.1.0"

# Lightweight public surface for notebooks and demo scripts.
from .agents import AgentOrchestrator
from .data import SyntheticDataService
from .forecasting import ForecastingService
from .optimizer import ConstraintAwareOptimizer

__all__ = [
    "AgentOrchestrator",
    "ConstraintAwareOptimizer",
    "ForecastingService",
    "SyntheticDataService",
    "__version__",
]
