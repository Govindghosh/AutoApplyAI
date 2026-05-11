from sqlalchemy.orm import Session
from app.models.workflow import ApplicationWorkflow, WorkflowStep, WorkflowStatus
from app.models.job import Job
from app.services.event_service import EventService, EventType
from app.services.escalation_service import EscalationCompressionEngine
from app.services.personalization_service import OrchestrationPersonalizationService
from app.services.recovery_service import RecoveryCompressionService
from app.core.logging import logger
from datetime import datetime, timezone
import json

class WorkflowOrchestrator:
    @staticmethod
    def initialize_workflow(db: Session, job: Job, user_id: int) -> ApplicationWorkflow:
        """
        Decomposes a job application into a graph of discrete, stateful steps.
        """
        # Determine steps based on platform
        steps_config = [
            "NAVIGATE_TO_JOB",
            "AUTH_CHECK",
            "UPLOAD_RESUME",
            "FILL_BASIC_INFO",
            "HANDLE_CUSTOM_QUESTIONS",
            "SUBMIT_APPLICATION",
            "VERIFY_SUBMISSION"
        ]
        
        workflow = ApplicationWorkflow(
            job_id=job.id,
            user_id=user_id,
            platform_type=job.source or "Generic",
            status=WorkflowStatus.PENDING
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        
        # Create individual steps
        for name in steps_config:
            step = WorkflowStep(
                workflow_id=workflow.id,
                name=name,
                status=WorkflowStatus.PENDING
            )
            db.add(step)
            
        db.commit()
        logger.info(f"Initialized workflow {workflow.id} with {len(steps_config)} steps")
        return workflow

    @staticmethod
    def execute_next_step(db: Session, workflow_id: int):
        """
        Orchestrates the transition to the next incomplete step.
        Supports resume/replay and error recovery.
        """
        workflow = db.query(ApplicationWorkflow).filter(ApplicationWorkflow.id == workflow_id).first()
        if not workflow or workflow.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.PAUSED_FOR_HUMAN,
        ]:
            return
            
        next_step = db.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == workflow.id,
            WorkflowStep.status.in_([WorkflowStatus.PENDING, WorkflowStatus.FAILED])
        ).order_by(WorkflowStep.id).first()
        
        if not next_step:
            workflow.status = WorkflowStatus.COMPLETED
            db.commit()
            return
            
        # Update state for execution
        workflow.status = WorkflowStatus.RUNNING
        next_step.status = WorkflowStatus.RUNNING
        next_step.started_at = datetime.now(timezone.utc)
        next_step.attempts += 1
        db.commit()
        
        # Broadcast Telemetry
        EventService.emit(
            user_id=workflow.user_id,
            event_type=EventType.APPLYING_STARTED,
            payload={
                "workflow_id": workflow.id,
                "step_name": next_step.name,
                "attempt": next_step.attempts
            },
            resource_id=str(workflow.job_id)
        )
        
        return next_step

    @staticmethod
    def fail_step(db: Session, step_id: int, error_msg: str):
        step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if step:
            step.status = WorkflowStatus.FAILED
            step.error_log = error_msg
            step.completed_at = datetime.now(timezone.utc)
            if step.started_at:
                delta = step.completed_at - step.started_at
                step.duration_ms = int(delta.total_seconds() * 1000)

            workflow = db.query(ApplicationWorkflow).filter(
                ApplicationWorkflow.id == step.workflow_id
            ).first()
            if workflow:
                workflow.status = WorkflowStatus.FAILED
                workflow_steps = db.query(WorkflowStep).filter(
                    WorkflowStep.workflow_id == workflow.id
                ).order_by(WorkflowStep.id).all()
                recommendation = RecoveryCompressionService.recommend(
                    workflow,
                    step,
                    workflow_steps,
                ).to_dict()
                profile = OrchestrationPersonalizationService.get_or_create_profile(db, workflow.user_id)
                recommendation["personalized_guidance"] = OrchestrationPersonalizationService.personalize_recovery_guidance(
                    workflow,
                    step,
                    recommendation,
                    profile,
                )
                step.output_data = {
                    **(step.output_data or {}),
                    "failure_disposition": recommendation["action"],
                    "recovery_recommendation": recommendation,
                }
                EventService.emit(
                    workflow.user_id,
                    EventType.WORKFLOW_RECOVERY_RECOMMENDED,
                    {
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                        "step_name": step.name,
                        "action": recommendation["action"],
                        "confidence": recommendation["confidence"],
                        "safety_validated": recommendation["safety_validated"],
                    },
                    resource_id=str(workflow.job_id),
                    source_worker="WorkflowOrchestrator",
                )

            db.commit()

    @staticmethod
    def pause_step_for_human(db: Session, step_id: int, reason: str, output: dict = None):
        """
        Pauses a checkpoint behind an explicit human approval boundary.
        """
        step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step or step.status == WorkflowStatus.COMPLETED:
            return

        escalation = EscalationCompressionEngine.build_escalation(
            reason,
            workflow_id=step.workflow_id,
            step_id=step.id,
            step_name=step.name,
            context=output,
        )

        step.status = WorkflowStatus.PAUSED_FOR_HUMAN
        step.error_log = reason
        step.output_data = {
            **(output or {}),
            "escalation": escalation,
        }

        workflow = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.id == step.workflow_id
        ).first()
        if workflow:
            profile = OrchestrationPersonalizationService.get_or_create_profile(db, workflow.user_id)
            escalation["personalized"] = OrchestrationPersonalizationService.personalize_escalation(
                escalation,
                profile,
            )
            workflow.status = WorkflowStatus.PAUSED_FOR_HUMAN
            EventService.emit(
                workflow.user_id,
                EventType.WORKFLOW_ESCALATION_CREATED,
                {
                    "workflow_id": workflow.id,
                    "step_id": step.id,
                    "step_name": step.name,
                    "template": escalation["template"],
                    "priority": escalation["priority"],
                    "governance_boundary": escalation["governance_boundary"],
                },
                resource_id=str(workflow.job_id),
                source_worker="WorkflowOrchestrator",
            )

        db.commit()
            
    @staticmethod
    def complete_step(db: Session, step_id: int, output: dict = None):
        """
        Completes a step with idempotency guards to prevent duplicate transitions.
        """
        step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
        if not step or step.status == WorkflowStatus.COMPLETED:
            return # Already completed, avoid duplicate processing
            
        step.status = WorkflowStatus.COMPLETED
        step.completed_at = datetime.now(timezone.utc)
        step.output_data = output
        
        if step.started_at:
            delta = step.completed_at - step.started_at
            step.duration_ms = int(delta.total_seconds() * 1000)
            
        # Update overall workflow progress
        workflow = db.query(ApplicationWorkflow).filter(
            ApplicationWorkflow.id == step.workflow_id
        ).first()
        if workflow:
            workflow.current_step_index += 1
            
        db.commit()
        logger.info(f"Node IDEMPOTENTLY COMPLETED: {step.name} (Step ID: {step.id})")
