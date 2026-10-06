"""Deterministic synthetic fleet and microgrid data generation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import DEFAULT_FLEET_SIZE, DEMO_DATE, DEMO_SEED
from .schemas import EnergyPoint, FleetVehicle


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


@dataclass(frozen=True)
class SyntheticDataService:
    """Generate a repeatable small fleet and site profile without external data."""

    seed: int = DEMO_SEED

    def fleet(self, size: int = DEFAULT_FLEET_SIZE) -> list[FleetVehicle]:
        size = max(1, min(int(size), 50))
        vehicles: list[FleetVehicle] = []
        for index in range(size):
            # The small phase term makes a seeded scenario visibly varied while
            # avoiding pseudo-random state and making every response reproducible.
            phase = (self.seed + index * 7) % 11
            capacity = 54.0 + float((index * 9 + phase) % 31)
            soc = 0.47 + ((index * 13 + phase) % 31) / 100.0
            target = 0.76 + ((index * 5 + phase) % 12) / 100.0
            # A few vehicles arrive with surplus energy, making the V2G demo
            # observable while still preserving a meaningful departure target.
            if index % 5 == 0:
                soc = max(soc, 0.86)
                target = min(target, 0.78)
            arrival = 5 + ((index * 3 + phase) % 7)
            departure = 16 + ((index * 5 + phase) % 8)
            vehicles.append(
                FleetVehicle(
                    vehicle_id=f"EV-{index + 1:02d}",
                    battery_capacity_kwh=_round(capacity, 1),
                    soc=_round(min(soc, 0.96), 3),
                    target_soc=_round(min(max(target, 0.0), 0.95), 3),
                    departure_hour=departure,
                    arrival_hour=arrival,
                    max_charge_kw=_round(7.2 + (index % 4) * 1.8, 1),
                    max_discharge_kw=_round(3.6 + (index % 3) * 1.2, 1),
                    charge_efficiency=0.93,
                    discharge_efficiency=0.92,
                    can_v2g=index % 4 != 3,
                )
            )
        return vehicles

    def energy(self, horizon_hours: int = 24, start_hour: int = 0) -> list[EnergyPoint]:
        """Return a smooth commercial-site demand and rooftop-solar profile."""

        horizon_hours = max(1, min(int(horizon_hours), 24))
        points: list[EnergyPoint] = []
        for offset in range(horizon_hours):
            hour = (int(start_hour) + offset) % 24
            # Morning and evening occupancy peaks, with a small deterministic
            # weekday-like modulation.  Values are intentionally realistic but
            # synthetic and should never be interpreted as telemetry.
            morning = 13.0 * math.exp(-((hour - 8.0) / 2.7) ** 2)
            evening = 19.0 * math.exp(-((hour - 18.0) / 3.2) ** 2)
            overnight = 4.0 * math.exp(-((hour - 1.5) / 3.8) ** 2)
            modulation = ((self.seed % 9) - 4) * 0.18 + (offset % 6) * 0.12
            demand = 34.0 + morning + evening + overnight + modulation

            # Solar output is zero outside daylight and peaks around noon.
            daylight = max(0.0, math.sin(math.pi * (hour - 6) / 13.0)) if 6 <= hour <= 19 else 0.0
            solar = 31.0 * (daylight**1.25) * (0.96 + ((self.seed + offset) % 5) * 0.01)
            demand = max(0.0, demand)
            solar = max(0.0, solar)
            points.append(
                EnergyPoint(
                    hour=hour,
                    demand_kw=_round(demand),
                    solar_kw=_round(solar),
                    net_load_kw=_round(max(0.0, demand - solar)),
                )
            )
        return points

    def historical_energy(self, days: int = 7) -> list[EnergyPoint]:
        """Build a compact deterministic history used by forecast quality metrics."""

        history: list[EnergyPoint] = []
        for day in range(max(1, min(int(days), 30))):
            # Preserve a 24-hour shape while applying a small, deterministic
            # day-specific scale.  The API only exposes the current-day slice.
            scale = 1.0 + ((day * 3 + self.seed) % 7 - 3) * 0.008
            for point in self.energy(24, 0):
                demand = point.demand_kw * scale
                solar = point.solar_kw * (1.0 - (day % 3) * 0.015)
                history.append(
                    EnergyPoint(
                        hour=point.hour,
                        demand_kw=_round(demand),
                        solar_kw=_round(solar),
                        net_load_kw=_round(max(0.0, demand - solar)),
                    )
                )
        return history

    @property
    def demo_date(self) -> str:
        return DEMO_DATE
