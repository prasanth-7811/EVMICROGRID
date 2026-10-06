"""Constraint-aware deterministic EV charging and V2G scheduling."""

from __future__ import annotations

import hashlib
import json
import statistics
from dataclasses import dataclass

from .analytics import EnergyAnalyticsService
from .schemas import (
    FleetVehicle,
    ForecastPoint,
    HourlySchedule,
    RenewableSummary,
    TariffPoint,
    VehicleSchedule,
    VehicleScheduleSlot,
)


def _r(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _available(vehicle: FleetVehicle, hour: int) -> bool:
    """Whether a vehicle is plugged in during an absolute clock hour."""

    arrival = vehicle.arrival_hour
    departure = vehicle.departure_hour
    if arrival == departure:
        return True
    if arrival < departure:
        return arrival <= hour < departure
    # Overnight connection window, e.g. arrival 20:00 and departure 06:00.
    return hour >= arrival or hour < departure


@dataclass
class OptimizationResult:
    run_id: str
    total_cost: float
    baseline_cost: float
    cost_savings: float
    renewable_energy_kwh: float
    renewable_fraction: float
    grid_import_kwh: float
    peak_grid_kw: float
    v2g_energy_kwh: float
    schedules: list[VehicleSchedule]
    hourly_schedule: list[HourlySchedule]
    renewable_analysis: RenewableSummary
    constraint_checks: dict[str, object]
    violations: list[str]


class ConstraintAwareOptimizer:
    """A transparent greedy optimizer with explicit safety checks.

    The objective is lexicographic: satisfy departure targets and reserve SOC,
    then favor on-site solar, then lower import rates, then reduce peak import.
    It is intentionally small enough to audit in a demo and has no solver or
    network dependency.
    """

    def __init__(self, analytics: EnergyAnalyticsService | None = None) -> None:
        self.analytics = analytics or EnergyAnalyticsService()

    def optimize(
        self,
        vehicles: list[FleetVehicle],
        forecasts: list[ForecastPoint],
        tariffs: list[TariffPoint],
        *,
        reserve_soc: float = 0.20,
        include_v2g: bool = True,
        renewable_target: float = 0.55,
        start_hour: int = 0,
    ) -> OptimizationResult:
        if not forecasts:
            raise ValueError("at least one forecast point is required")
        horizon = len(forecasts)
        tariff_by_hour = {item.hour: item for item in tariffs}
        forecast_by_hour = {item.hour: item for item in forecasts}
        fallback_tariffs = self.analytics.tariffs(horizon, start_hour)
        for item in fallback_tariffs:
            tariff_by_hour.setdefault(item.hour, item)
        # Custom forecast arrays may use a different start hour than the
        # request. Fill any remaining lookup gaps by deriving a tariff directly
        # from that forecast hour rather than raising a KeyError.
        for forecast in forecasts:
            if forecast.hour not in tariff_by_hour:
                tariff_by_hour[forecast.hour] = self.analytics.tariffs(1, forecast.hour)[0]

        # Each map stores input-side charging/discharging power for one vehicle.
        charge_plan: dict[str, list[float]] = {
            vehicle.vehicle_id: [0.0] * horizon for vehicle in vehicles
        }
        discharge_plan: dict[str, list[float]] = {
            vehicle.vehicle_id: [0.0] * horizon for vehicle in vehicles
        }
        vehicle_violations: dict[str, list[str]] = {vehicle.vehicle_id: [] for vehicle in vehicles}

        for vehicle in vehicles:
            goal_soc = max(float(reserve_soc), float(vehicle.target_soc))
            required_input = max(0.0, (goal_soc - vehicle.soc) * vehicle.battery_capacity_kwh)
            required_input /= max(vehicle.charge_efficiency, 1e-9)
            available_indices = [
                index
                for index, forecast in enumerate(forecasts)
                if _available(vehicle, forecast.hour)
            ]
            # Solar-rich hours first, then low tariff, then chronological order.
            ranked_for_charge = sorted(
                available_indices,
                key=lambda index: (
                    -forecast_by_hour[forecasts[index].hour].solar_kw,
                    tariff_by_hour[forecasts[index].hour].import_rate_per_kwh,
                    forecasts[index].hour,
                ),
            )
            remaining = required_input
            for index in ranked_for_charge:
                if remaining <= 1e-9:
                    break
                amount = min(vehicle.max_charge_kw, remaining)
                charge_plan[vehicle.vehicle_id][index] = _r(amount, 6)
                remaining -= amount
            if remaining > 1e-6:
                vehicle_violations[vehicle.vehicle_id].append(
                    "departure target cannot be reached within the available connection window"
                )

        # V2G is only scheduled above the goal SOC.  This means the safety
        # invariant can be verified locally while still demonstrating discharge
        # on high-price/high-load periods for vehicles with surplus energy.
        all_rates = [item.import_rate_per_kwh for item in tariff_by_hour.values()]
        high_rate = statistics.median(all_rates) if all_rates else 0.2
        net_loads = [point.net_load_kw for point in forecasts]
        load_threshold = statistics.median(net_loads) if net_loads else 0.0
        for vehicle in vehicles:
            if not include_v2g or not vehicle.can_v2g or vehicle.max_discharge_kw <= 0:
                continue
            goal_soc = max(float(reserve_soc), float(vehicle.target_soc))
            candidate_indices = sorted(
                [
                    index
                    for index, forecast in enumerate(forecasts)
                    if _available(vehicle, forecast.hour)
                    and tariff_by_hour[forecast.hour].import_rate_per_kwh >= high_rate
                    and forecast.net_load_kw >= load_threshold
                ],
                key=lambda index: (
                    -tariff_by_hour[forecasts[index].hour].import_rate_per_kwh,
                    -forecasts[index].net_load_kw,
                    forecasts[index].hour,
                ),
            )
            # Simulate in chronological order to determine the surplus available
            # at each candidate. Charging is applied before V2G in a time slot.
            soc = vehicle.soc
            for index, forecast in enumerate(forecasts):
                soc += charge_plan[vehicle.vehicle_id][index] * vehicle.charge_efficiency / vehicle.battery_capacity_kwh
                if index not in candidate_indices:
                    continue
                surplus_output = max(
                    0.0,
                    (soc - goal_soc) * vehicle.battery_capacity_kwh * vehicle.discharge_efficiency,
                )
                amount = min(vehicle.max_discharge_kw, surplus_output, forecast.demand_kw)
                if amount > 1e-9:
                    discharge_plan[vehicle.vehicle_id][index] = _r(amount, 6)
                    soc -= amount / vehicle.discharge_efficiency / vehicle.battery_capacity_kwh

        vehicle_schedules: list[VehicleSchedule] = []
        for vehicle in vehicles:
            soc = float(vehicle.soc)
            slots: list[VehicleScheduleSlot] = []
            energy_charged = 0.0
            energy_discharged = 0.0
            for index, forecast in enumerate(forecasts):
                charge = charge_plan[vehicle.vehicle_id][index]
                discharge = discharge_plan[vehicle.vehicle_id][index]
                soc += charge * vehicle.charge_efficiency / vehicle.battery_capacity_kwh
                soc -= discharge / max(vehicle.discharge_efficiency, 1e-9) / vehicle.battery_capacity_kwh
                soc = max(0.0, min(1.0, soc))
                energy_charged += charge
                energy_discharged += discharge
                slots.append(
                    VehicleScheduleSlot(
                        hour=forecast.hour,
                        charge_kw=_r(charge),
                        discharge_kw=_r(discharge),
                        soc=_r(soc),
                        available=_available(vehicle, forecast.hour),
                    )
                )
            # Check the final state and every slot against hard safety limits.
            violations = list(vehicle_violations[vehicle.vehicle_id])
            if vehicle.soc < reserve_soc - 1e-5:
                violations.append("initial SOC is below the configured reserve")
            for slot in slots:
                if slot.soc < reserve_soc - 1e-5:
                    violations.append(f"reserve SOC breached at hour {slot.hour}")
                if slot.charge_kw > vehicle.max_charge_kw + 1e-5:
                    violations.append(f"charge power exceeded at hour {slot.hour}")
                if slot.discharge_kw > vehicle.max_discharge_kw + 1e-5:
                    violations.append(f"discharge power exceeded at hour {slot.hour}")
                if slot.charge_kw > 1e-6 and slot.discharge_kw > 1e-6:
                    violations.append(f"simultaneous charge and discharge at hour {slot.hour}")
                if not slot.available and (slot.charge_kw > 1e-6 or slot.discharge_kw > 1e-6):
                    violations.append(f"vehicle not connected at hour {slot.hour}")
            final_soc = slots[-1].soc if slots else vehicle.soc
            departure_target_met = final_soc + 1e-5 >= max(vehicle.target_soc, reserve_soc)
            if not departure_target_met and "departure target cannot be reached within the available connection window" not in violations:
                violations.append("departure target not met")
            vehicle_schedules.append(
                VehicleSchedule(
                    vehicle_id=vehicle.vehicle_id,
                    slots=slots,
                    initial_soc=_r(vehicle.soc),
                    final_soc=_r(final_soc),
                    target_soc=_r(vehicle.target_soc),
                    energy_charged_kwh=_r(energy_charged),
                    energy_discharged_kwh=_r(energy_discharged),
                    departure_target_met=departure_target_met,
                    constraint_violations=sorted(set(violations)),
                )
            )

        hourly: list[HourlySchedule] = []
        for index, forecast in enumerate(forecasts):
            charge = sum(charge_plan[vehicle.vehicle_id][index] for vehicle in vehicles)
            discharge = sum(discharge_plan[vehicle.vehicle_id][index] for vehicle in vehicles)
            direct_solar = min(forecast.demand_kw, forecast.solar_kw)
            solar_to_ev = min(max(0.0, forecast.solar_kw - direct_solar), charge)
            grid_import = max(0.0, forecast.demand_kw + charge - forecast.solar_kw - discharge)
            tariff = tariff_by_hour[forecast.hour]
            cost = grid_import * tariff.import_rate_per_kwh
            site_load = forecast.demand_kw + charge
            renewable_fraction = min(1.0, (direct_solar + solar_to_ev) / site_load) if site_load else 0.0
            hourly.append(
                HourlySchedule(
                    hour=forecast.hour,
                    base_demand_kw=_r(forecast.demand_kw),
                    solar_kw=_r(forecast.solar_kw),
                    ev_charge_kw=_r(charge),
                    ev_discharge_kw=_r(discharge),
                    grid_import_kw=_r(grid_import),
                    solar_to_ev_kw=_r(solar_to_ev),
                    renewable_fraction=_r(renewable_fraction),
                    import_rate_per_kwh=_r(tariff.import_rate_per_kwh),
                    cost=_r(cost),
                )
            )

        total_cost = sum(slot.cost for slot in hourly)
        base_cost = self.analytics.baseline_cost(forecasts, list(tariff_by_hour.values()))
        total_charge = sum(item.ev_charge_kw for item in hourly)
        max_rate = max((item.import_rate_per_kwh for item in hourly), default=0.2)
        # The baseline assumes unmanaged EV energy is bought in the peak period;
        # this makes the comparison meaningful without claiming a real tariff.
        baseline_cost = base_cost + total_charge * max_rate
        grid_import = sum(item.grid_import_kw for item in hourly)
        peak_grid = max((item.grid_import_kw for item in hourly), default=0.0)
        direct_solar = sum(min(item.base_demand_kw, item.solar_kw) for item in hourly)
        ev_solar = sum(item.solar_to_ev_kw for item in hourly)
        solar_generation = sum(item.solar_kw for item in hourly)
        site_demand = sum(item.base_demand_kw + item.ev_charge_kw for item in hourly)
        renewable_energy = min(site_demand, direct_solar + ev_solar)
        renewable_fraction = renewable_energy / site_demand if site_demand else 0.0
        cleanest = sorted(hourly, key=lambda item: (-item.renewable_fraction, item.hour))[:5]
        renewable_analysis = RenewableSummary(
            total_demand_kwh=_r(site_demand),
            solar_generation_kwh=_r(solar_generation),
            direct_solar_kwh=_r(direct_solar),
            renewable_fraction=_r(renewable_fraction),
            curtailment_kwh=_r(max(0.0, solar_generation - direct_solar - ev_solar)),
            cleanest_hours=[item.hour for item in cleanest],
        )

        violations = sorted(
            {
                violation
                for schedule in vehicle_schedules
                for violation in schedule.constraint_violations
            }
        )
        checks = {
            "all_constraints_satisfied": not violations,
            "reserve_soc_respected": all(
                slot.soc >= reserve_soc - 1e-5
                for schedule in vehicle_schedules
                for slot in schedule.slots
            ),
            "departure_targets_met": all(schedule.departure_target_met for schedule in vehicle_schedules),
            "charge_power_limits_respected": all(
                slot.charge_kw <= vehicle.max_charge_kw + 1e-5
                for vehicle in vehicles
                for schedule in vehicle_schedules
                if schedule.vehicle_id == vehicle.vehicle_id
                for slot in schedule.slots
            ),
            "discharge_power_limits_respected": all(
                slot.discharge_kw <= vehicle.max_discharge_kw + 1e-5
                for vehicle in vehicles
                for schedule in vehicle_schedules
                if schedule.vehicle_id == vehicle.vehicle_id
                for slot in schedule.slots
            ),
            "no_simultaneous_charge_discharge": all(
                not (slot.charge_kw > 1e-6 and slot.discharge_kw > 1e-6)
                for schedule in vehicle_schedules
                for slot in schedule.slots
            ),
            "renewable_target_met": renewable_fraction + 1e-9 >= renewable_target,
            "renewable_target": _r(renewable_target),
        }
        payload = {
            "vehicles": [vehicle.model_dump(mode="json") for vehicle in vehicles],
            "hours": [forecast.model_dump(mode="json") for forecast in forecasts],
            "tariffs": [tariff.model_dump(mode="json") for tariff in tariffs],
            "reserve_soc": reserve_soc,
            "v2g": include_v2g,
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:10]
        return OptimizationResult(
            run_id=f"opt-{digest}",
            total_cost=_r(total_cost),
            baseline_cost=_r(baseline_cost),
            cost_savings=_r(baseline_cost - total_cost),
            renewable_energy_kwh=_r(renewable_energy),
            renewable_fraction=_r(renewable_fraction),
            grid_import_kwh=_r(grid_import),
            peak_grid_kw=_r(peak_grid),
            v2g_energy_kwh=_r(sum(item.ev_discharge_kw for item in hourly)),
            schedules=vehicle_schedules,
            hourly_schedule=hourly,
            renewable_analysis=renewable_analysis,
            constraint_checks=checks,
            violations=violations,
        )


# Friendly aliases for callers that prefer shorter names.
ChargingOptimizer = ConstraintAwareOptimizer
Optimizer = ConstraintAwareOptimizer
