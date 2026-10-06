"""Tariff, renewable, and baseline-cost analysis for the demo microgrid."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import ForecastPoint, RenewableSummary, TariffPoint


def _r(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


@dataclass(frozen=True)
class EnergyAnalyticsService:
    """Transparent time-of-use tariff and renewable calculations."""

    def tariffs(self, horizon_hours: int = 24, start_hour: int = 0) -> list[TariffPoint]:
        points: list[TariffPoint] = []
        for offset in range(max(1, min(int(horizon_hours), 24))):
            hour = (int(start_hour) + offset) % 24
            if 0 <= hour < 6:
                period, import_rate = "off_peak", 0.11
            elif 6 <= hour < 16:
                period, import_rate = "solar_window", 0.17
            elif 16 <= hour < 21:
                period, import_rate = "evening_peak", 0.31
            else:
                period, import_rate = "shoulder", 0.20
            # Export is intentionally lower than import to model a conservative
            # net-metering assumption and discourage speculative discharge.
            export_rate = 0.055 if period == "solar_window" else 0.075
            renewable_intensity = {
                "off_peak": 0.42,
                "solar_window": 0.78,
                "evening_peak": 0.28,
                "shoulder": 0.48,
            }[period]
            points.append(
                TariffPoint(
                    hour=hour,
                    import_rate_per_kwh=import_rate,
                    export_rate_per_kwh=export_rate,
                    period=period,
                    renewable_intensity=renewable_intensity,
                )
            )
        return points

    def renewable_analysis(
        self,
        forecasts: list[ForecastPoint],
        direct_solar_kwh: float | None = None,
        ev_solar_kwh: float = 0.0,
    ) -> RenewableSummary:
        total_demand = sum(point.demand_kw for point in forecasts)
        generation = sum(point.solar_kw for point in forecasts)
        if direct_solar_kwh is None:
            direct_solar_kwh = sum(min(point.demand_kw, point.solar_kw) for point in forecasts)
        direct_solar_kwh = max(0.0, min(float(direct_solar_kwh), generation))
        ev_solar_kwh = max(0.0, min(float(ev_solar_kwh), max(0.0, generation - direct_solar_kwh)))
        renewable_energy = min(total_demand, direct_solar_kwh + ev_solar_kwh)
        cleanest = sorted(
            forecasts,
            key=lambda point: (-point.solar_kw / max(point.demand_kw, 1.0), point.hour),
        )[: min(5, len(forecasts))]
        return RenewableSummary(
            total_demand_kwh=_r(total_demand),
            solar_generation_kwh=_r(generation),
            direct_solar_kwh=_r(direct_solar_kwh),
            renewable_fraction=_r(renewable_energy / total_demand if total_demand else 0.0),
            curtailment_kwh=_r(max(0.0, generation - direct_solar_kwh - ev_solar_kwh)),
            cleanest_hours=[point.hour for point in cleanest],
        )

    def baseline_cost(self, forecasts: list[ForecastPoint], tariffs: list[TariffPoint]) -> float:
        rates = {tariff.hour: tariff.import_rate_per_kwh for tariff in tariffs}
        return _r(sum(point.demand_kw * rates.get(point.hour, 0.2) for point in forecasts))

    def renewable_signal(self, forecast: ForecastPoint) -> float:
        """A bounded score used by the optimizer to prioritize solar charging."""

        return max(0.0, min(1.0, forecast.solar_kw / max(forecast.demand_kw, 1.0)))
