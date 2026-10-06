"""Deterministic orchestration of forecasting, analysis, optimization, and RAG."""

from __future__ import annotations

from dataclasses import dataclass
from .analytics import EnergyAnalyticsService
from .config import (
    DEFAULT_FLEET_SIZE,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_RENEWABLE_TARGET,
    DEFAULT_RESERVE_SOC,
    DEMO_DATE,
    DEMO_SEED,
    MODEL_VERSION,
)
from .data import SyntheticDataService
from .feedback import FeedbackStore
from .forecasting import ForecastingService
from .knowledge import PolicyRetriever
from .monitoring import MonitoringService
from .optimizer import ConstraintAwareOptimizer
from .recommendations import RecommendationEngine
from .schemas import (
    AgentStatus,
    DashboardResponse,
    EnergyPoint,
    FeedbackRequest,
    FeedbackResponse,
    FleetVehicle,
    ForecastPoint,
    OptimizationRequest,
    OptimizationResponse,
    PolicyEvidence,
    TariffPoint,
    MonitoringResponse,
)


@dataclass
class ScenarioContext:
    fleet: list[FleetVehicle]
    energy: list[EnergyPoint]
    forecasts: list[ForecastPoint]
    tariffs: list[TariffPoint]
    policy_evidence: list[PolicyEvidence]
    quality: dict[str, float | int | str]


class AgentOrchestrator:
    """Coordinate local specialist agents while retaining an auditable trace."""

    def __init__(self, seed: int = DEMO_SEED) -> None:
        self.seed = seed
        self.data = SyntheticDataService(seed=seed)
        self.forecaster = ForecastingService(self.data)
        self.analytics = EnergyAnalyticsService()
        self.optimizer = ConstraintAwareOptimizer(self.analytics)
        self.retriever = PolicyRetriever()
        self.recommender = RecommendationEngine()
        self.feedback_store = FeedbackStore()
        self.monitor = MonitoringService(self.feedback_store)
        # Seed quality monitoring with the deterministic baseline so a direct
        # GET /api/monitoring is informative even before the first dashboard call.
        baseline_forecast = self.forecaster.forecast(DEFAULT_HORIZON_HOURS, 0)
        self.monitor.record_quality(
            self.forecaster.quality_snapshot(baseline_forecast, self.data.energy(DEFAULT_HORIZON_HOURS, 0))
        )

    def agent_statuses(self) -> list[AgentStatus]:
        return [
            AgentStatus(
                agent_id="data-synthesizer",
                name="Data Synthesizer",
                role="Creates deterministic fleet and energy scenarios",
                status="ready",
                capabilities=["fleet generation", "load profile", "solar profile"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="forecast-agent",
                name="Forecast Agent",
                role="Forecasts demand and rooftop solar with uncertainty bands",
                status="ready",
                capabilities=["demand forecast", "solar forecast", "quality metrics"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="tariff-agent",
                name="Tariff Analyst",
                role="Scores time-of-use rates and renewable intensity",
                status="ready",
                capabilities=["tariff analysis", "renewable analysis", "cost baseline"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="charging-optimizer",
                name="Charging Optimizer",
                role="Schedules charging and bounded V2G under explicit constraints",
                status="ready",
                capabilities=["charge scheduling", "V2G", "constraint checks"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="policy-guardian",
                name="Policy Guardian",
                role="Retrieves local policy evidence for grounded outputs",
                status="ready",
                capabilities=["local retrieval", "policy citations", "guardrails"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="explanation-agent",
                name="Explanation Agent",
                role="Turns metrics and policy evidence into operator recommendations",
                status="ready",
                capabilities=["explanations", "impact estimates", "human review prompts"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
            AgentStatus(
                agent_id="monitoring-agent",
                name="Monitoring Agent",
                role="Tracks request health, forecast quality, drift, and feedback",
                status="ready",
                capabilities=["quality metrics", "drift indicators", "feedback capture"],
                last_run=f"{DEMO_DATE}T00:00:00Z",
            ),
        ]

    def _context(
        self,
        *,
        horizon_hours: int = DEFAULT_HORIZON_HOURS,
        start_hour: int = 0,
        fleet_size: int = DEFAULT_FLEET_SIZE,
        seed: int | None = None,
        vehicles: list[FleetVehicle] | None = None,
        forecasts: list[ForecastPoint] | None = None,
        tariffs: list[TariffPoint] | None = None,
    ) -> ScenarioContext:
        if seed is not None and seed != self.seed:
            # Construct a local service rather than mutating orchestrator state,
            # so one request cannot change subsequent deterministic requests.
            data = SyntheticDataService(seed=seed)
            forecaster = ForecastingService(data)
        else:
            data = self.data
            forecaster = self.forecaster
        horizon_hours = max(1, min(int(horizon_hours), 24))
        fleet = list(vehicles) if vehicles else data.fleet(fleet_size)
        energy = data.energy(horizon_hours, start_hour)
        predicted = list(forecasts) if forecasts else forecaster.forecast(horizon_hours, start_hour)
        # Complete short custom forecasts from the deterministic model, while
        # preserving user-provided points. This keeps the optimizer total.
        if len(predicted) < horizon_hours:
            generated = forecaster.forecast(horizon_hours, start_hour)
            by_hour = {item.hour: item for item in predicted}
            predicted = [by_hour.get(item.hour, item) for item in generated]
        else:
            predicted = predicted[:horizon_hours]
        supplied_tariffs = list(tariffs) if tariffs else []
        generated_tariffs = self.analytics.tariffs(horizon_hours, start_hour)
        supplied_by_hour = {item.hour: item for item in supplied_tariffs}
        generated_by_hour = {item.hour: item for item in generated_tariffs}
        # Align tariff points to the forecast hours. Supplied points win when a
        # caller provides the same hour; missing/misaligned points are filled by
        # the deterministic local TOU profile.
        tariff_points = [
            supplied_by_hour.get(forecast.hour, generated_by_hour.get(forecast.hour, generated_tariffs[index]))
            for index, forecast in enumerate(predicted)
        ]
        quality = forecaster.quality_snapshot(predicted, energy)
        self.monitor.record_quality(quality)
        query = "charging solar renewable tariff V2G departure safety operator review"
        evidence = self.retriever.retrieve(query, top_k=5)
        return ScenarioContext(
            fleet=fleet,
            energy=energy,
            forecasts=predicted,
            tariffs=tariff_points,
            policy_evidence=evidence,
            quality=quality,
        )

    @staticmethod
    def _trace(agent_id: str, output: str) -> dict[str, str]:
        # Deliberately omit wall-clock duration so snapshots stay deterministic.
        return {"agent_id": agent_id, "status": "complete", "output": output}

    def optimize(
        self,
        request: OptimizationRequest,
        *,
        record_request: bool = True,
    ) -> OptimizationResponse:
        context = self._context(
            horizon_hours=request.horizon_hours,
            start_hour=request.start_hour,
            fleet_size=request.fleet_size,
            seed=request.seed,
            vehicles=request.vehicles,
            forecasts=request.forecast,
            tariffs=request.tariffs,
        )
        result = self.optimizer.optimize(
            context.fleet,
            context.forecasts,
            context.tariffs,
            reserve_soc=request.reserve_soc,
            include_v2g=request.include_v2g,
            renewable_target=request.renewable_target,
            start_hour=request.start_hour,
        )
        target_met = bool(result.constraint_checks.get("departure_targets_met", False))
        recommendations = self.recommender.generate(
            context.forecasts,
            context.tariffs,
            renewable=result.renewable_analysis,
            hourly_schedule=result.hourly_schedule,
            policy_evidence=context.policy_evidence,
            target_fraction=request.renewable_target,
            target_met=target_met,
        )
        if record_request:
            self.monitor.record_request("optimization")
        response_summary: dict[str, float | int | str] = {
            "total_cost": result.total_cost,
            "baseline_cost": result.baseline_cost,
            "cost_savings": result.cost_savings,
            "renewable_fraction": result.renewable_fraction,
            "grid_import_kwh": result.grid_import_kwh,
            "peak_grid_kw": result.peak_grid_kw,
            "v2g_energy_kwh": result.v2g_energy_kwh,
            "constraint_status": "passed" if not result.violations else "review",
        }
        return OptimizationResponse(
            run_id=result.run_id,
            horizon_hours=request.horizon_hours,
            start_hour=request.start_hour,
            objective="departure readiness → renewable-first → tariff cost → peak reduction",
            total_cost=result.total_cost,
            baseline_cost=result.baseline_cost,
            cost_savings=result.cost_savings,
            renewable_energy_kwh=result.renewable_energy_kwh,
            renewable_fraction=result.renewable_fraction,
            grid_import_kwh=result.grid_import_kwh,
            peak_grid_kw=result.peak_grid_kw,
            v2g_energy_kwh=result.v2g_energy_kwh,
            schedules=result.schedules,
            vehicle_schedules=result.schedules,
            schedule=result.hourly_schedule,
            hourly_schedule=result.hourly_schedule,
            hourly=result.hourly_schedule,
            forecasts=context.forecasts,
            tariffs=context.tariffs,
            renewable_analysis=result.renewable_analysis,
            constraint_checks=result.constraint_checks,
            summary=response_summary,
            violations=result.violations,
            recommendations=recommendations,
            policy_evidence=context.policy_evidence,
            agent_trace=[
                self._trace("data-synthesizer", f"prepared {len(context.fleet)} vehicles"),
                self._trace("forecast-agent", f"forecasted {len(context.forecasts)} hours; quality={context.quality['status']}"),
                self._trace("tariff-agent", f"analyzed {len(context.tariffs)} tariff periods"),
                self._trace("charging-optimizer", f"checked {len(result.schedules)} vehicle schedules"),
                self._trace("policy-guardian", f"retrieved {len(context.policy_evidence)} local policy snippets"),
                self._trace("explanation-agent", f"generated {len(recommendations)} recommendations"),
                self._trace("monitoring-agent", "updated quality and drift indicators"),
            ],
        )

    def dashboard(self) -> DashboardResponse:
        context = self._context()
        # A dashboard uses the same optimizer path as the API so its cards and
        # recommendation panel are internally consistent.
        request = OptimizationRequest(
            horizon_hours=len(context.forecasts),
            fleet_size=len(context.fleet),
            vehicles=context.fleet,
            forecast=context.forecasts,
            tariffs=context.tariffs,
            seed=self.seed,
            reserve_soc=DEFAULT_RESERVE_SOC,
            renewable_target=DEFAULT_RENEWABLE_TARGET,
        )
        optimization = self.optimize(request, record_request=False)
        self.monitor.record_request("dashboard")
        summary: dict[str, float | int | str] = {
            "total_vehicles": len(context.fleet),
            "connected_vehicles": sum(1 for vehicle in context.fleet if vehicle.arrival_hour <= vehicle.departure_hour),
            "total_demand_kwh": optimization.renewable_analysis.total_demand_kwh,
            "solar_generation_kwh": optimization.renewable_analysis.solar_generation_kwh,
            "renewable_fraction": optimization.renewable_fraction,
            "grid_import_kwh": optimization.grid_import_kwh,
            "peak_grid_kw": optimization.peak_grid_kw,
            "estimated_cost_savings": optimization.cost_savings,
            "v2g_energy_kwh": optimization.v2g_energy_kwh,
            "forecast_trend": self.forecaster.trend_label(context.forecasts),
            "active_recommendations": len(optimization.recommendations),
            "optimization_run_id": optimization.run_id,
        }
        return DashboardResponse(
            dashboard_version=MODEL_VERSION,
            deterministic=True,
            summary=summary,
            fleet=context.fleet,
            fleet_summary={
                "total_vehicles": len(context.fleet),
                "v2g_capable": sum(1 for vehicle in context.fleet if vehicle.can_v2g),
                "average_soc": round(sum(vehicle.soc for vehicle in context.fleet) / len(context.fleet), 3),
            },
            energy=context.energy,
            energy_summary={
                "total_demand_kwh": optimization.renewable_analysis.total_demand_kwh,
                "solar_generation_kwh": optimization.renewable_analysis.solar_generation_kwh,
                "grid_import_kwh": optimization.grid_import_kwh,
            },
            forecasts=context.forecasts,
            forecast=context.forecasts,
            tariffs=context.tariffs,
            tariff=context.tariffs,
            metrics=summary,
            renewable_analysis=optimization.renewable_analysis,
            recommendations=optimization.recommendations,
            agents=self.agent_statuses(),
            monitoring=self.monitor.snapshot(),
        )

    def feedback(self, request: FeedbackRequest) -> FeedbackResponse:
        record = self.feedback_store.add(request)
        self.monitor.record_request("feedback")
        return FeedbackResponse(feedback=record, aggregate=self.feedback_store.aggregate())

    def monitoring(self) -> MonitoringResponse:
        return self.monitor.snapshot()
