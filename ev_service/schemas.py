"""Pydantic schemas shared by the API and the deterministic service modules."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class APIModel(BaseModel):
    """Base model with predictable JSON behavior and forward-compatible input."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class HealthResponse(APIModel):
    status: str
    service: str
    version: str
    deterministic: bool
    local_only: bool
    demo_date: str
    components: dict[str, str]


class FleetVehicle(APIModel):
    vehicle_id: str = Field(min_length=1)
    battery_capacity_kwh: float = Field(gt=0)
    soc: float = Field(ge=0.0, le=1.0)
    target_soc: float = Field(ge=0.0, le=1.0)
    departure_hour: int = Field(ge=0, le=23)
    arrival_hour: int = Field(ge=0, le=23)
    max_charge_kw: float = Field(gt=0)
    max_discharge_kw: float = Field(ge=0)
    charge_efficiency: float = Field(gt=0, le=1)
    discharge_efficiency: float = Field(gt=0, le=1)
    can_v2g: bool = True

    @field_validator("target_soc")
    @classmethod
    def target_not_below_zero(cls, value: float) -> float:
        return float(value)


class EnergyPoint(APIModel):
    hour: int = Field(ge=0, le=23)
    demand_kw: float = Field(ge=0)
    solar_kw: float = Field(ge=0)
    net_load_kw: float = Field(ge=0)


class ForecastPoint(APIModel):
    hour: int = Field(ge=0, le=23)
    demand_kw: float = Field(ge=0)
    solar_kw: float = Field(ge=0)
    net_load_kw: float = Field(ge=0)
    demand_lower_kw: float = Field(ge=0)
    demand_upper_kw: float = Field(ge=0)
    solar_lower_kw: float = Field(ge=0)
    solar_upper_kw: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class TariffPoint(APIModel):
    hour: int = Field(ge=0, le=23)
    import_rate_per_kwh: float = Field(ge=0)
    export_rate_per_kwh: float = Field(ge=0)
    period: str
    renewable_intensity: float = Field(ge=0, le=1)


class RenewableSummary(APIModel):
    total_demand_kwh: float = Field(ge=0)
    solar_generation_kwh: float = Field(ge=0)
    direct_solar_kwh: float = Field(ge=0)
    renewable_fraction: float = Field(ge=0, le=1)
    curtailment_kwh: float = Field(ge=0)
    cleanest_hours: list[int] = Field(default_factory=list)


class VehicleScheduleSlot(APIModel):
    hour: int = Field(ge=0, le=23)
    charge_kw: float = Field(ge=0)
    discharge_kw: float = Field(ge=0)
    soc: float = Field(ge=0, le=1)
    available: bool = True


class VehicleSchedule(APIModel):
    vehicle_id: str
    slots: list[VehicleScheduleSlot] = Field(default_factory=list)
    initial_soc: float = Field(ge=0, le=1)
    final_soc: float = Field(ge=0, le=1)
    target_soc: float = Field(ge=0, le=1)
    energy_charged_kwh: float = Field(ge=0)
    energy_discharged_kwh: float = Field(ge=0)
    departure_target_met: bool
    constraint_violations: list[str] = Field(default_factory=list)


class HourlySchedule(APIModel):
    hour: int = Field(ge=0, le=23)
    base_demand_kw: float = Field(ge=0)
    solar_kw: float = Field(ge=0)
    ev_charge_kw: float = Field(ge=0)
    ev_discharge_kw: float = Field(ge=0)
    grid_import_kw: float = Field(ge=0)
    solar_to_ev_kw: float = Field(ge=0)
    renewable_fraction: float = Field(ge=0, le=1)
    import_rate_per_kwh: float = Field(ge=0)
    cost: float = Field(ge=0)


class PolicyEvidence(APIModel):
    policy_id: str
    title: str
    source: str
    snippet: str
    score: float = Field(ge=0)
    matched_terms: list[str] = Field(default_factory=list)


class Recommendation(APIModel):
    recommendation_id: str
    priority: Literal["high", "medium", "low"]
    title: str
    message: str
    rationale: str
    expected_impact: dict[str, float | str] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    policy_references: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class AgentStatus(APIModel):
    agent_id: str
    name: str
    role: str
    status: Literal["ready", "running", "degraded"]
    deterministic: bool = True
    capabilities: list[str] = Field(default_factory=list)
    last_run: str | None = None


class AgentListResponse(APIModel):
    agents: list[AgentStatus]
    count: int
    deterministic: bool
    orchestration_mode: str


class OptimizationRequest(APIModel):
    horizon_hours: int = Field(default=24, ge=1, le=24)
    start_hour: int = Field(default=0, ge=0, le=23)
    fleet_size: int = Field(default=8, ge=1, le=50)
    include_v2g: bool = True
    reserve_soc: float = Field(default=0.20, ge=0, le=1)
    renewable_target: float = Field(default=0.55, ge=0, le=1)
    seed: int = 42
    vehicles: list[FleetVehicle] | None = None
    forecast: list[ForecastPoint] | None = None
    tariffs: list[TariffPoint] | None = None

    @field_validator("reserve_soc", "renewable_target", mode="before")
    @classmethod
    def accept_percent_or_fraction(cls, value: float | None) -> float | None:
        """Accept UI-friendly percentages (30) as well as fractions (0.30)."""

        if value is None:
            return value
        numeric = float(value)
        return numeric / 100.0 if numeric > 1.0 else numeric


class OptimizationResponse(APIModel):
    run_id: str
    horizon_hours: int
    start_hour: int
    objective: str
    total_cost: float = Field(ge=0)
    baseline_cost: float = Field(ge=0)
    cost_savings: float
    renewable_energy_kwh: float = Field(ge=0)
    renewable_fraction: float = Field(ge=0, le=1)
    grid_import_kwh: float = Field(ge=0)
    peak_grid_kw: float = Field(ge=0)
    v2g_energy_kwh: float = Field(ge=0)
    schedules: list[VehicleSchedule] = Field(default_factory=list)
    # Compatibility aliases make the response convenient for small dashboards
    # that use either singular or descriptive collection names.
    vehicle_schedules: list[VehicleSchedule] = Field(default_factory=list)
    schedule: list[HourlySchedule] = Field(default_factory=list)
    hourly_schedule: list[HourlySchedule] = Field(default_factory=list)
    hourly: list[HourlySchedule] = Field(default_factory=list)
    forecasts: list[ForecastPoint] = Field(default_factory=list)
    tariffs: list[TariffPoint] = Field(default_factory=list)
    renewable_analysis: RenewableSummary
    constraint_checks: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, float | int | str] = Field(default_factory=dict)
    violations: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    policy_evidence: list[PolicyEvidence] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackRequest(APIModel):
    recommendation_id: str | None = None
    run_id: str | None = None
    rating: int = Field(ge=1, le=5)
    helpful: bool | None = None
    comment: str = Field(default="", max_length=2000)
    category: Literal["accuracy", "cost", "usability", "policy", "other"] = "other"


class FeedbackRecord(APIModel):
    feedback_id: str
    recommendation_id: str | None = None
    run_id: str | None = None
    rating: int = Field(ge=1, le=5)
    helpful: bool | None = None
    comment: str = ""
    category: str = "other"
    captured_at: str


class FeedbackResponse(APIModel):
    status: Literal["accepted"] = "accepted"
    feedback: FeedbackRecord
    aggregate: dict[str, float | int]


class MonitoringResponse(APIModel):
    status: Literal["healthy", "degraded"]
    service_version: str
    requests: dict[str, int]
    quality: dict[str, float | int | str]
    drift: dict[str, float | int | str]
    feedback: dict[str, float | int]
    checks: dict[str, bool]


class DashboardResponse(APIModel):
    dashboard_version: str
    deterministic: bool
    summary: dict[str, float | int | str]
    fleet: list[FleetVehicle]
    fleet_summary: dict[str, float | int | str] = Field(default_factory=dict)
    energy: list[EnergyPoint]
    energy_summary: dict[str, float | int | str] = Field(default_factory=dict)
    forecasts: list[ForecastPoint]
    forecast: list[ForecastPoint] = Field(default_factory=list)
    tariffs: list[TariffPoint]
    tariff: list[TariffPoint] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    renewable_analysis: RenewableSummary
    recommendations: list[Recommendation]
    agents: list[AgentStatus]
    monitoring: MonitoringResponse
