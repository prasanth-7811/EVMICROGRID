"""Deterministic request, quality, drift, and feedback monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import MODEL_VERSION
from .feedback import FeedbackStore
from .schemas import MonitoringResponse


@dataclass
class MonitoringService:
    feedback_store: FeedbackStore
    requests_total: int = 0
    dashboard_requests: int = 0
    optimization_requests: int = 0
    feedback_requests: int = 0
    errors_total: int = 0
    _last_quality: dict[str, float | int | str] = field(default_factory=dict)
    _last_drift: dict[str, float | int | str] = field(default_factory=dict)

    def record_request(self, kind: str) -> None:
        self.requests_total += 1
        if kind == "dashboard":
            self.dashboard_requests += 1
        elif kind == "optimization":
            self.optimization_requests += 1
        elif kind == "feedback":
            self.feedback_requests += 1

    def record_error(self) -> None:
        self.errors_total += 1

    def record_quality(self, quality: dict[str, float | int | str]) -> None:
        self._last_quality = dict(quality)
        mae = float(quality.get("mae_kw", 0.0))
        coverage = float(quality.get("interval_coverage", 1.0))
        # The baseline is synthetic and fixed.  Drift is a transparent distance
        # from that baseline, not a claim about a production data distribution.
        self._last_drift = {
            "demand_mae_delta_kw": round(max(0.0, mae - 1.5), 3),
            "interval_coverage_delta": round(coverage - 0.90, 3),
            "drift_score": round(min(1.0, max(0.0, max(0.0, mae - 1.5) / 5.0)), 3),
            "status": "nominal" if mae <= 3.0 and coverage >= 0.80 else "review",
        }

    def snapshot(self) -> MonitoringResponse:
        quality = {
            "mae_kw": float(self._last_quality.get("mae_kw", 0.0)),
            "solar_mae_kw": float(self._last_quality.get("solar_mae_kw", 0.0)),
            "interval_coverage": float(self._last_quality.get("interval_coverage", 1.0)),
            "samples": int(self._last_quality.get("samples", 0)),
            "status": str(self._last_quality.get("status", "nominal")),
        }
        drift = {
            "demand_mae_delta_kw": float(self._last_drift.get("demand_mae_delta_kw", 0.0)),
            "interval_coverage_delta": float(self._last_drift.get("interval_coverage_delta", 0.0)),
            "drift_score": float(self._last_drift.get("drift_score", 0.0)),
            "status": str(self._last_drift.get("status", "nominal")),
        }
        feedback = self.feedback_store.aggregate()
        healthy = self.errors_total == 0 and drift["status"] == "nominal"
        return MonitoringResponse(
            status="healthy" if healthy else "degraded",
            service_version=MODEL_VERSION,
            requests={
                "total": self.requests_total,
                "dashboard": self.dashboard_requests,
                "optimization": self.optimization_requests,
                "feedback": self.feedback_requests,
                "errors": self.errors_total,
            },
            quality=quality,
            drift=drift,
            feedback=feedback,
            checks={
                "deterministic_local_mode": True,
                "forecast_quality_available": quality["samples"] > 0,
                "feedback_store_available": True,
                "constraint_monitor_available": True,
            },
        )
