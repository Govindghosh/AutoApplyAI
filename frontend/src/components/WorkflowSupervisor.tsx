"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { appConfig } from "@/lib/config";
import type { WorkflowDetails, WorkflowStep } from "@/lib/types";
import { InlineLoading, ListSkeleton, LoadingHalo } from "@/components/LoadingStates";
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Clock,
  Database,
  Download,
  Flag,
  PauseCircle,
  Play,
  Power,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Terminal,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

const statusStyle: Record<string, string> = {
  COMPLETED: "bg-green-500/10 border-green-500 text-green-500",
  RUNNING: "bg-blue-500/10 border-blue-500 text-blue-500 animate-pulse",
  FAILED: "bg-red-500/10 border-red-500 text-red-500",
  PAUSED_FOR_HUMAN: "bg-amber-500/10 border-amber-500 text-amber-400",
  PENDING: "bg-slate-900 border-slate-800 text-slate-600",
};

function StepIcon({ step }: { step: WorkflowStep }) {
  if (step.status === "COMPLETED") return <CheckCircle2 size={20} />;
  if (step.status === "RUNNING") return <Play size={20} fill="currentColor" />;
  if (step.status === "FAILED") return <AlertCircle size={20} />;
  if (step.status === "PAUSED_FOR_HUMAN") return <PauseCircle size={20} />;
  return <Circle size={20} />;
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function WorkflowSupervisor({ workflowId, onClose }: { workflowId: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const telemetrySentFor = useRef<number | null>(null);

  const { data, isLoading } = useQuery<WorkflowDetails>({
    queryKey: ["workflow", workflowId],
    queryFn: () => backendApi.workflows.get(workflowId),
    refetchInterval: appConfig.workflowRefreshMs,
  });

  const refreshWorkflow = () => {
    queryClient.invalidateQueries({ queryKey: ["workflow", workflowId] });
  };

  const activeStep = useMemo(
    () => data?.steps.find((step) => ["RUNNING", "PAUSED_FOR_HUMAN", "FAILED"].includes(step.status)),
    [data?.steps]
  );

  const recordRecoveryHintAction = (action: string, step?: WorkflowStep) => {
    if (!step?.explanation?.recovery_hint) return;

    void backendApi.transparency.productEvent(
      "recovery_hint_actioned",
      {
        workflow_id: workflowId,
        step_id: step.id,
        step_name: step.name,
        action,
        hint: step.explanation.recovery_hint,
      },
      data?.workflow.job_id ? String(data.workflow.job_id) : undefined
    );
  };

  useEffect(() => {
    const loadedWorkflowId = data?.workflow.id || workflowId;
    if (!data || telemetrySentFor.current === loadedWorkflowId) return;

    telemetrySentFor.current = loadedWorkflowId;
    void backendApi.transparency.productEvent(
      "workflow_supervisor_opened",
      {
        workflow_id: loadedWorkflowId,
        workflow_status: data.workflow.status,
        active_step_name: activeStep?.name || null,
        visible_recovery_hints: data.steps.filter((step) => step.explanation?.recovery_hint).length,
      },
      data.workflow.job_id ? String(data.workflow.job_id) : undefined
    );
  }, [activeStep?.name, data, workflowId]);

  const retryMutation = useMutation({
    mutationFn: (step: WorkflowStep) => {
      recordRecoveryHintAction("retry_step", step);
      return backendApi.workflows.retryStep(workflowId, step.id);
    },
    onSuccess: () => {
      setNotice("Checkpoint replay queued.");
      refreshWorkflow();
    },
  });

  const replayMutation = useMutation({
    mutationFn: () => {
      recordRecoveryHintAction("replay_last_checkpoint", activeStep);
      return backendApi.workflows.replayLastCheckpoint(workflowId);
    },
    onSuccess: () => {
      setNotice("Last failed or paused checkpoint queued.");
      refreshWorkflow();
    },
  });

  const reportMutation = useMutation({
    mutationFn: (step: WorkflowStep) =>
      backendApi.workflows.reportStep(workflowId, step.id, step.explanation?.why || step.error),
    onSuccess: () => {
      setNotice("Node report recorded.");
      refreshWorkflow();
    },
  });

  const terminateMutation = useMutation({
    mutationFn: (reason?: string) => backendApi.workflows.terminate(workflowId, reason),
    onSuccess: () => {
      setNotice("Workflow terminated.");
      refreshWorkflow();
    },
  });

  const exportTrace = async () => {
    setIsExporting(true);
    try {
      const trace = await backendApi.transparency.trace(workflowId);
      downloadJson(`workflow-${workflowId}-trace.json`, trace);
      setNotice("Workflow trace exported.");
    } finally {
      setIsExporting(false);
    }
  };

  const terminateWorkflow = () => {
    if (window.confirm("Terminate this workflow and mark the application as failed?")) {
      const reason = activeStep
        ? `user_requested_during_${activeStep.status.toLowerCase()}`
        : "user_requested";
      terminateMutation.mutate(reason);
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[200] flex items-center justify-end">
        <div className="w-full max-w-2xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
          <header className="p-6 border-b border-slate-800">
            <LoadingHalo label="Opening supervisor" detail={`Workflow ID ${workflowId}`} />
          </header>
          <div className="border-b border-slate-800 bg-slate-950/40 p-6">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
              <div className="h-full w-1/2 animate-pulse rounded-full bg-blue-400" />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-8">
            <ListSkeleton count={5} />
          </div>
        </div>
      </div>
    );
  }

  const summary = data?.workflow.summary;

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-[200] flex items-center justify-end">
      <div className="w-full max-w-2xl h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
        <header className="p-6 border-b border-slate-800 flex items-start justify-between gap-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className={`w-2 h-2 rounded-full ${data?.workflow.status === "PAUSED_FOR_HUMAN" ? "bg-amber-400" : "bg-green-500 animate-pulse"}`} />
              <h2 className="text-xl font-black text-white tracking-tight uppercase">Workflow Supervisor</h2>
            </div>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">
              Platform: {data?.workflow.platform} &middot; Workflow ID: {workflowId}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 transition-colors" title="Close">
            <X size={24} />
          </button>
        </header>

        <div className="border-b border-slate-800 bg-slate-950/40 p-6 space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-black text-white">{summary?.headline || "Workflow state unavailable"}</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-400">{summary?.autonomy_boundary}</p>
            </div>
            <div className="text-right shrink-0">
              <span className="text-2xl font-black text-white">{summary?.progress_percent ?? 0}%</span>
              <p className="text-[10px] uppercase tracking-widest text-slate-500">
                {summary?.completed_steps ?? 0}/{summary?.total_steps ?? 0} checkpoints
              </p>
            </div>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-blue-400 transition-all duration-700"
              style={{ width: `${summary?.progress_percent ?? 0}%` }}
            />
          </div>
          {notice && (
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-xs font-bold text-blue-200">
              {notice}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-8 space-y-8">
          <div className="relative">
            <div className="absolute left-[19px] top-4 bottom-4 w-0.5 bg-slate-800" />

            <div className="space-y-10">
              {data?.steps.map((step) => {
                const explanation = step.explanation;

                return (
                  <div key={step.id} className="relative flex gap-6 group">
                    <div className={`relative z-10 w-10 h-10 rounded-lg flex items-center justify-center border-2 transition-all ${statusStyle[step.status] || statusStyle.PENDING}`}>
                      <StepIcon step={step} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="min-w-0">
                          <h4 className={`text-sm font-black tracking-widest uppercase ${step.status === "RUNNING" ? "text-white" : "text-slate-300"}`}>
                            {explanation?.label || step.name.replace(/_/g, " ")}
                          </h4>
                          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                            <span>{explanation?.status_text || step.status.replace(/_/g, " ")}</span>
                            <span>&middot;</span>
                            <span>{explanation?.autonomy || "supervised"}</span>
                            {step.started_at && (
                              <>
                                <span>&middot;</span>
                                <span className="flex items-center gap-1">
                                  <Clock size={12} />
                                  {new Date(step.started_at).toLocaleTimeString()}
                                </span>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="flex gap-2 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                          {step.status === "FAILED" && (
                            <button
                              onClick={() => retryMutation.mutate(step)}
                              disabled={retryMutation.isPending}
                              className="p-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg border border-red-500/20 disabled:opacity-50"
                              title="Replay checkpoint"
                            >
                              {retryMutation.isPending && retryMutation.variables?.id === step.id ? (
                                <InlineLoading label="" tone="amber" />
                              ) : (
                                <RotateCcw size={14} />
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => reportMutation.mutate(step)}
                            disabled={reportMutation.isPending}
                            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 rounded-lg border border-slate-700 disabled:opacity-50"
                            title="Report node"
                          >
                            {reportMutation.isPending && reportMutation.variables?.id === step.id ? (
                              <InlineLoading label="" />
                            ) : (
                              <Flag size={14} />
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-4 space-y-4">
                        <p className="text-sm leading-relaxed text-slate-300">{explanation?.why || explanation?.summary}</p>

                        {explanation?.data_used && explanation.data_used.length > 0 && (
                          <div>
                            <div className="mb-2 flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-slate-500">
                              <Database size={12} />
                              Data used
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {explanation.data_used.map((item) => (
                                <span key={item} className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                  {item}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {explanation?.recovery_hint && (
                          <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs leading-relaxed text-amber-100/80">
                            {explanation.recovery_hint}
                          </div>
                        )}

                        {step.status === "COMPLETED" && typeof step.duration === "number" && (
                          <div className="flex items-center gap-2 text-[10px] text-slate-600 font-bold uppercase tracking-widest">
                            <ShieldCheck size={12} />
                            Execution Time: {(step.duration / 1000).toFixed(2)}s
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <footer className="p-6 border-t border-slate-800 bg-slate-950/50">
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={exportTrace}
              disabled={isExporting}
              className="py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 border border-slate-700"
            >
              {isExporting ? (
                <InlineLoading label="EXPORTING" />
              ) : (
                <>
                  <Download size={16} className="text-blue-400" />
                  EXPORT TRACE
                </>
              )}
            </button>
            <button
              onClick={() => replayMutation.mutate()}
              disabled={replayMutation.isPending}
              className="py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 border border-slate-700 disabled:opacity-50"
            >
              {replayMutation.isPending ? (
                <InlineLoading label="REPLAYING" tone="amber" />
              ) : (
                <>
                  <RefreshCw size={16} className="text-amber-400" />
                  REPLAY LAST
                </>
              )}
            </button>
            <button
              onClick={() => refreshWorkflow()}
              className="py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-bold text-sm transition-all flex items-center justify-center gap-2 border border-slate-700"
            >
              <Terminal size={16} className="text-slate-400" />
              REFRESH STATE
            </button>
            <button
              onClick={terminateWorkflow}
              disabled={terminateMutation.isPending}
              className="py-3 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg font-bold text-sm transition-all border border-red-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {terminateMutation.isPending ? (
                <InlineLoading label="TERMINATING" tone="amber" />
              ) : (
                <>
                  <Power size={16} />
                  TERMINATE
                </>
              )}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
