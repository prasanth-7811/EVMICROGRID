"""FastAPI application for the deterministic EV energy microgrid demo."""

from __future__ import annotations

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .agents import AgentOrchestrator
from .config import DASHBOARD_DIR, DEMO_DATE, DEMO_SEED, MODEL_VERSION
from .schemas import (
    AgentListResponse,
    DashboardResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    MonitoringResponse,
    OptimizationRequest,
    OptimizationResponse,
)


orchestrator = AgentOrchestrator(seed=DEMO_SEED)

app = FastAPI(
    title="EV Energy Microgrid Intelligence Demo",
    version=MODEL_VERSION,
    description=(
        "Offline, deterministic fleet charging intelligence with synthetic data, "
        "policy-grounded explanations, and monitoring metrics."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return a lightweight readiness signal with no external dependencies."""

    return HealthResponse(
        status="ok",
        service="ev-energy-microgrid",
        version=MODEL_VERSION,
        deterministic=True,
        local_only=True,
        demo_date=DEMO_DATE,
        components={
            "synthetic_data": "ready",
            "forecasting": "ready",
            "optimizer": "ready",
            "policy_retrieval": "ready",
            "monitoring": "ready",
        },
    )


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard() -> DashboardResponse:
    return orchestrator.dashboard()


@app.get("/api/agents", response_model=AgentListResponse)
def agents() -> AgentListResponse:
    statuses = orchestrator.agent_statuses()
    return AgentListResponse(
        agents=statuses,
        count=len(statuses),
        deterministic=True,
        orchestration_mode="local-specialist-agents",
    )


@app.post("/api/optimize", response_model=OptimizationResponse)
def optimize(request: OptimizationRequest | None = Body(default=None)) -> OptimizationResponse:
    """Optimize the default scenario when the caller sends an empty body."""

    return orchestrator.optimize(request or OptimizationRequest())


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    return orchestrator.feedback(request)


@app.get("/api/monitoring", response_model=MonitoringResponse)
def monitoring() -> MonitoringResponse:
    return orchestrator.monitoring()


# Keep this mount last: API and OpenAPI routes must win over the dashboard's
# catch-all root mount.  StaticFiles(html=True) serves dashboard/index.html at /.
app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
