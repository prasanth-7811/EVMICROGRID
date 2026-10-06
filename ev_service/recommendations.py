"""Explainable, policy-grounded recommendation generation."""

from __future__ import annotations

from dataclasses import dataclass

from .schemas import (
    ForecastPoint,
    HourlySchedule,
    PolicyEvidence,
    Recommendation,
    RenewableSummary,
    TariffPoint,
)


def _r(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


@dataclass
class RecommendationEngine:
    """Create concise recommendations from measured demo metrics only."""

    def generate(
        self,
        forecasts: list[ForecastPoint],
        tariffs: list[TariffPoint],
        *,
        renewable: RenewableSummary | None = None,
        hourly_schedule: list[HourlySchedule] | None = None,
        policy_evidence: list[PolicyEvidence] | None = None,
        target_fraction: float = 0.55,
        target_met: bool = True,
    ) -> list[Recommendation]:
        evidence = policy_evidence or []
        by_id = {item.policy_id: item for item in evidence}

        def refs(*ids: str) -> list[str]:
            selected = [policy_id for policy_id in ids if policy_id in by_id]
            if selected:
                return selected
            return [item.policy_id for item in evidence[:1]]

        recommendations: list[Recommendation] = []
        high_tariff = max(tariffs, key=lambda item: (item.import_rate_per_kwh, -item.hour)) if tariffs else None
        solar_hours = sorted(forecasts, key=lambda item: (-item.solar_kw, item.hour))[:3]
        solar_fraction = renewable.renewable_fraction if renewable else 0.0
        curtailment = renewable.curtailment_kwh if renewable else 0.0
        peak_grid = max((item.grid_import_kw for item in (hourly_schedule or [])), default=0.0)

        # Recommendation 1: tariff-aware flexible charging.
        if high_tariff is not None:
            recommendations.append(
                Recommendation(
                    recommendation_id="rec-tariff-shift",
                    priority="high" if high_tariff.import_rate_per_kwh >= 0.30 else "medium",
                    title="Shift flexible charging away from the evening peak",
                    message=(
                        f"Prefer lower-rate windows before {high_tariff.hour:02d}:00 where departure targets remain feasible. "
                        f"The modeled peak import rate is ${high_tariff.import_rate_per_kwh:.2f}/kWh."
                    ),
                    rationale="The optimizer ranks feasible hours by renewable availability and time-of-use price.",
                    expected_impact={"peak_rate_per_kwh": _r(high_tariff.import_rate_per_kwh), "peak_hour": high_tariff.hour},
                    actions=["Review flexible vehicles first", "Keep each vehicle's departure target and reserve unchanged"],
                    policy_references=refs("EV-POL-004", "EV-POL-001"),
                    confidence=0.93,
                )
            )

        # Recommendation 2: renewable-first charging / curtailment.
        best_hours = ", ".join(f"{item.hour:02d}:00" for item in solar_hours)
        recommendations.append(
            Recommendation(
                recommendation_id="rec-solar-first",
                priority="high" if curtailment > 5 else "medium",
                title="Use the solar window for flexible EV energy",
                message=(
                    f"Prioritize available on-site solar around {best_hours or 'midday'} before importing energy. "
                    f"Modeled renewable coverage is {solar_fraction:.0%}."
                ),
                rationale="Solar-to-EV allocation is reported separately so operators can see direct use and curtailment.",
                expected_impact={"renewable_fraction": _r(solar_fraction), "curtailment_kwh": _r(curtailment)},
                actions=["Enable renewable-first ordering", "Inspect remaining curtailment before adding load"],
                policy_references=refs("EV-POL-003"),
                confidence=0.90,
            )
        )

        # Recommendation 3: V2G / safety guardrail, included even when no
        # discharge is scheduled so the operator sees the policy boundary.
        recommendations.append(
            Recommendation(
                recommendation_id="rec-v2g-guardrail",
                priority="medium",
                title="Keep V2G inside reserve and departure guardrails",
                message=(
                    "Only V2G-capable vehicles with surplus energy should discharge during high-load periods; "
                    "retain the configured reserve and verify departure readiness."
                ),
                rationale=(
                    f"The current modeled peak grid import is {peak_grid:.1f} kW; discharge is treated as a bounded "
                    "peak-support action rather than an autonomous command."
                ),
                expected_impact={"peak_grid_kw": _r(peak_grid), "target_met": str(bool(target_met)).lower()},
                actions=["Review V2G eligibility", "Require operator approval for live dispatch"],
                policy_references=refs("EV-POL-002", "EV-POL-005"),
                confidence=0.88,
            )
        )

        if not target_met:
            recommendations.insert(
                0,
                Recommendation(
                    recommendation_id="rec-target-risk",
                    priority="high",
                    title="Review an unmet departure target",
                    message="At least one modeled vehicle cannot reach its requested departure target within the connection window.",
                    rationale="The constraint checker reported insufficient available charging time or power.",
                    expected_impact={"target_met": "false"},
                    actions=["Extend the connection window", "Reduce the target only with operator approval"],
                    policy_references=refs("EV-POL-001", "EV-POL-005"),
                    confidence=0.98,
                ),
            )
        return recommendations
