"""Local demand and solar forecasting with deterministic uncertainty bands."""

from __future__ import annotations

from dataclasses import dataclass, field

from .data import SyntheticDataService
from .schemas import EnergyPoint, ForecastPoint


def _r(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


@dataclass
class ForecastingService:
    data_service: SyntheticDataService = field(default_factory=SyntheticDataService)

    def forecast(self, horizon_hours: int = 24, start_hour: int = 0) -> list[ForecastPoint]:
        """Forecast the next horizon using a transparent seasonal baseline.

        This is deliberately not a black-box ML model: the demo can explain the
        output and reproduce it offline.  A small hour-dependent adjustment
        mimics forecast bias and produces useful confidence bands.
        """

        actual = self.data_service.energy(horizon_hours, start_hour)
        output: list[ForecastPoint] = []
        for offset, point in enumerate(actual):
            hour = point.hour
            # Stable bias is derived from the hour and seed, not wall-clock time.
            demand_bias = (((hour * 5 + self.data_service.seed) % 9) - 4) * 0.11
            solar_bias = (((hour * 3 + self.data_service.seed) % 7) - 3) * 0.07
            demand = max(0.0, point.demand_kw + demand_bias)
            solar = max(0.0, point.solar_kw + solar_bias)
            horizon_penalty = min(0.10, offset * 0.004)
            confidence = max(0.84, 0.97 - horizon_penalty)
            demand_spread = demand * (0.055 + horizon_penalty)
            solar_spread = max(0.8, solar * (0.12 + horizon_penalty * 1.3))
            output.append(
                ForecastPoint(
                    hour=hour,
                    demand_kw=_r(demand),
                    solar_kw=_r(solar),
                    net_load_kw=_r(max(0.0, demand - solar)),
                    demand_lower_kw=_r(max(0.0, demand - demand_spread)),
                    demand_upper_kw=_r(demand + demand_spread),
                    solar_lower_kw=_r(max(0.0, solar - solar_spread)),
                    solar_upper_kw=_r(solar + solar_spread),
                    confidence=_r(confidence, 3),
                )
            )
        return output

    def quality_snapshot(
        self,
        forecasts: list[ForecastPoint],
        actual: list[EnergyPoint] | None = None,
    ) -> dict[str, float | int | str]:
        """Return deterministic error and interval-coverage indicators."""

        actual = actual or self.data_service.energy(len(forecasts), forecasts[0].hour if forecasts else 0)
        by_hour = {point.hour: point for point in actual}
        paired = [(forecast, by_hour.get(forecast.hour)) for forecast in forecasts]
        paired = [(forecast, point) for forecast, point in paired if point is not None]
        if not paired:
            return {"mae_kw": 0.0, "solar_mae_kw": 0.0, "interval_coverage": 1.0, "samples": 0, "status": "no_data"}
        demand_errors = [abs(forecast.demand_kw - point.demand_kw) for forecast, point in paired]
        solar_errors = [abs(forecast.solar_kw - point.solar_kw) for forecast, point in paired]
        covered = [
            forecast.demand_lower_kw <= point.demand_kw <= forecast.demand_upper_kw
            for forecast, point in paired
        ]
        return {
            "mae_kw": _r(sum(demand_errors) / len(demand_errors)),
            "solar_mae_kw": _r(sum(solar_errors) / len(solar_errors)),
            "interval_coverage": _r(sum(covered) / len(covered), 3),
            "samples": len(paired),
            "status": "nominal",
        }

    @staticmethod
    def trend_label(forecasts: list[ForecastPoint]) -> str:
        if not forecasts:
            return "stable"
        first = forecasts[0].net_load_kw
        last = forecasts[-1].net_load_kw
        delta = last - first
        if delta > 8:
            return "rising"
        if delta < -8:
            return "falling"
        # Compare the midday valley to the edges for a useful human label.
        minimum = min(point.net_load_kw for point in forecasts)
        if minimum < first - 10:
            return "solar_relief"
        return "stable"
