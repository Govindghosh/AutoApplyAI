from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.models.event import SystemEvent
from app.services.behavioral_metrics_service import BehavioralMetricsService
from app.services.event_service import EventType
from app.services.pattern_analysis_service import PatternAnalysisService
from app.services.safety_throttle_service import SafetyThrottleService
from app.services.signal_integrity_service import SignalIntegrityService
from app.core.logging import logger
from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/operations", tags=["operations"])

@router.get("/stats")
async def get_operational_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Provides real-time SLO and product-friction metrics for beta validation.
    """
    total_workflows = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id
    ).count()
    completed_workflows = db.query(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        ApplicationWorkflow.status == WorkflowStatus.COMPLETED
    ).count()
    
    # Recovery Success Rate (Resumed after failure/pause)
    recovered = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        WorkflowStep.attempts > 1,
        WorkflowStep.status == WorkflowStatus.COMPLETED
    ).count()
    
    # Mean Intervention Rate
    escalated = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        WorkflowStep.status == WorkflowStatus.PAUSED_FOR_HUMAN
    ).count()
    
    # Mean Workflow Duration
    avg_duration = db.query(func.avg(WorkflowStep.duration_ms)).join(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        WorkflowStep.status == WorkflowStatus.COMPLETED
    ).scalar() or 0

    approval_latency_ms = db.query(func.avg(WorkflowStep.duration_ms)).join(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        WorkflowStep.name == "SUBMIT_APPLICATION",
        WorkflowStep.status == WorkflowStatus.COMPLETED,
        WorkflowStep.duration_ms.isnot(None),
    ).scalar() or 0

    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    stale_interventions = db.query(WorkflowStep).join(ApplicationWorkflow).filter(
        ApplicationWorkflow.user_id == current_user.id,
        WorkflowStep.status == WorkflowStatus.PAUSED_FOR_HUMAN,
        WorkflowStep.started_at <= stale_cutoff,
    ).count()

    reported_events = db.query(SystemEvent).filter(
        SystemEvent.user_id == current_user.id,
        SystemEvent.event_type == EventType.WORKFLOW_NODE_REPORTED.value,
    ).all()
    confusion_points: dict[str, int] = {}
    for event in reported_events:
        step_name = (event.payload or {}).get("step_name", "unknown")
        confusion_points[step_name] = confusion_points.get(step_name, 0) + 1

    top_confusion_points = [
        {"step_name": step_name, "reports": reports}
        for step_name, reports in sorted(
            confusion_points.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]
    ]

    behavioral_validation = BehavioralMetricsService.build(
        db,
        current_user.id,
        total_workflows,
        stale_interventions,
    )
    pattern_analysis = PatternAnalysisService.build(db, current_user.id)
    signal_integrity = SignalIntegrityService.build(db, current_user.id)

    return {
        "slo": {
            "completion_rate": (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0,
            "recovery_success_rate": (recovered / total_workflows * 100) if total_workflows > 0 else 0,
            "intervention_frequency": (escalated / total_workflows) if total_workflows > 0 else 0,
            "mean_node_duration_ms": float(avg_duration)
        },
        "throughput": {
            "total_active_workflows": db.query(ApplicationWorkflow).filter(
                ApplicationWorkflow.user_id == current_user.id,
                ApplicationWorkflow.status == WorkflowStatus.RUNNING
            ).count(),
            "total_nodes_executed": db.query(WorkflowStep).join(ApplicationWorkflow).filter(
                ApplicationWorkflow.user_id == current_user.id
            ).count()
        },
        "safety": SafetyThrottleService.get_usage(db, current_user),
        "beta_observability": {
            "onboarding_completions": db.query(SystemEvent).filter(
                SystemEvent.user_id == current_user.id,
                SystemEvent.event_type == EventType.ONBOARDING_COMPLETED.value,
            ).count(),
            "active_interventions": escalated,
            "stale_interventions": stale_interventions,
            "approval_latency_ms": float(approval_latency_ms),
            "reported_nodes": len(reported_events),
            "trace_exports": db.query(SystemEvent).filter(
                SystemEvent.user_id == current_user.id,
                SystemEvent.event_type == EventType.WORKFLOW_TRACE_EXPORTED.value,
            ).count(),
            "repeated_user_corrections": db.query(WorkflowStep).join(ApplicationWorkflow).filter(
                ApplicationWorkflow.user_id == current_user.id,
                WorkflowStep.attempts > 1,
            ).count(),
            "confusion_points": top_confusion_points,
        },
        "behavioral_validation": behavioral_validation,
        "pattern_analysis": pattern_analysis,
        "signal_integrity": signal_integrity,
    }

@router.post("/chaos/trigger")
async def trigger_chaos(scenario: str, db: Session = Depends(get_db)):
    """
    INTERNAL ONLY: Injects synthetic failures into the orchestration engine.
    """
    logger.warning(f"CHAOS INJECTED: Scenario -> {scenario}")
    
    if scenario == "kill_worker_mid_node":
        # Simulate worker death by failing the most recent running step
        step = db.query(WorkflowStep).filter(
            WorkflowStep.status == WorkflowStatus.RUNNING
        ).order_by(WorkflowStep.started_at.desc()).first()
        if step:
            step.status = WorkflowStatus.FAILED
            step.error_log = "SYNTHETIC FAILURE: Worker termination simulated."
            db.commit()
            return {"status": "injected", "target_step": step.id}
            
    elif scenario == "simulate_redis_outage":
        # Logic to temporarily disable Redis publisher
        pass
        
    return {"status": "scenario_not_found"}
