"use client";

import { useQuery } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { appConfig } from "@/lib/config";
import type { OperationsStats } from "@/lib/types";
import {
  Activity, 
  ShieldCheck, 
  Zap, 
  Users, 
  BarChart3,
  Timer,
  AlertCircle,
  Flag,
  Shield,
  Brain,
  RotateCcw,
  TrendingUp,
  UserCheck,
} from "lucide-react";

const emptyBehavioralValidation: OperationsStats["behavioral_validation"] = {
  intervention_confusion_rate: 0,
  confusion_signal_count: 0,
  explainability: {
    supervisor_opens: 0,
    recovery_hint_actions: 0,
    explanation_to_recovery_rate: 0,
  },
  human_escalation: {
    resolved: 0,
    pending: 0,
    failed: 0,
    success_rate: 0,
  },
  replay: {
    attempts: 0,
    successes: 0,
    loops: 0,
    success_rate: 0,
    outcomes_by_step: [],
  },
  termination: {
    count: 0,
    reasons: [],
    by_step: [],
  },
  trust_retention: {
    continuation_actions: 0,
    termination_actions: 0,
    retention_rate: 0,
  },
};

const emptySafety: OperationsStats["safety"] = {
  daily_started: 0,
  daily_limit: appConfig.dailyApplicationLimit,
  daily_remaining: appConfig.dailyApplicationLimit,
  active_workflows: 0,
  concurrency_limit: appConfig.workflowConcurrencyLimit,
  concurrency_remaining: appConfig.workflowConcurrencyLimit,
};

const emptyBetaObservability: OperationsStats["beta_observability"] = {
  onboarding_completions: 0,
  active_interventions: 0,
  stale_interventions: 0,
  approval_latency_ms: 0,
  reported_nodes: 0,
  trace_exports: 0,
  repeated_user_corrections: 0,
  confusion_points: [],
};

const emptyPatternAnalysis: OperationsStats["pattern_analysis"] = {
  analysis_guardrails: {
    directional_sample_size: 5,
    stable_sample_size: 20,
    note: "Pattern analysis is observational until enough samples accumulate.",
  },
  node_patterns: [],
  explanation_patterns: [],
  ats_friction: [],
  intervention_fatigue: {
    total_interventions: 0,
    interventions_per_workflow: 0,
    interventions_per_successful_application: 0,
    high_fatigue_workflows: 0,
    confidence: "insufficient",
    risk_level: "unknown",
  },
  trust_decay: {
    terminated_workflows: 0,
    termination_rate: 0,
    average_failed_recoveries_before_termination: 0,
    confidence: "insufficient",
    risk_level: "unknown",
  },
  summary: {
    top_confusion_node: null,
    top_confusion_node_confidence: "insufficient",
    highest_friction_platform: null,
    highest_friction_platform_confidence: "insufficient",
    fatigue_risk_level: "unknown",
    trust_decay_risk_level: "unknown",
  },
  sample: {
    workflows: 0,
    steps: 0,
    events: 0,
    confidence: "insufficient",
  },
};

const emptySignalIntegrity: OperationsStats["signal_integrity"] = {
  guardrails: {
    note: "Signal integrity validation is observational and does not mutate orchestration policy.",
    minimums: {
      observe: 5,
      directional: 20,
      stable: 50,
    },
    temporal_windows_days: {
      recent: 7,
      baseline: 21,
    },
    decay_half_life_days: 14,
  },
  sample_quality: {
    overall_confidence: "insufficient",
    workflows: 0,
    steps: 0,
    events: 0,
    metric_samples: [],
    platform_coverage: [],
    interpretation: "No signal available yet.",
  },
  temporal_stability: {
    recent_window_days: 7,
    baseline_window_days: 21,
    recent_samples: 0,
    baseline_samples: 0,
    comparisons: [],
    overall_stability: "insufficient",
    interpretation: "Temporal comparison needs both recent and baseline workflow samples.",
  },
  causation_guards: [],
  segment_analysis: {
    current_user_segment: "no_usage",
    behavior_flags: ["no_strong_segment_signal"],
    workflows: 0,
    interventions_per_workflow: 0,
    replays: 0,
    reports: 0,
    terminations: 0,
    aggregate_caveat: "This endpoint is user-scoped.",
  },
  signal_decay: {
    half_life_days: 14,
    raw_workflows: 0,
    decayed_workflow_weight: 0,
    raw_events: 0,
    decayed_event_weight: 0,
    stale_signal_share: 0,
    interpretation: "No signal available yet.",
  },
  summary: {
    optimization_readiness: "observe_only",
    overall_confidence: "insufficient",
    temporal_stability: "insufficient",
    causation_guard_count: 0,
    stale_signal_share: 0,
  },
};

const confidenceColor = (confidence: string) => {
  if (confidence === "stable") return "text-green-400 border-green-500/20 bg-green-500/10";
  if (confidence === "directional") return "text-amber-400 border-amber-500/20 bg-amber-500/10";
  if (confidence === "observe_only") return "text-blue-400 border-blue-500/20 bg-blue-500/10";
  return "text-slate-400 border-slate-700 bg-slate-800";
};

const riskColor = (risk: string) => {
  if (risk === "high") return "text-red-400";
  if (risk === "medium") return "text-amber-400";
  if (risk === "low") return "text-green-400";
  return "text-slate-400";
};

export default function OperationsPage() {
  const { data: stats, isLoading } = useQuery<OperationsStats>({
    queryKey: ["operations-stats"],
    queryFn: () => backendApi.operations.stats(),
    refetchInterval: appConfig.operationsRefreshMs,
  });

  if (isLoading || !stats) return <div className="p-8 text-slate-500 animate-pulse">Loading operational proof...</div>;

  const behavior = stats.behavioral_validation ?? emptyBehavioralValidation;
  const safety = stats.safety ?? emptySafety;
  const betaObservability = stats.beta_observability ?? emptyBetaObservability;
  const pattern = stats.pattern_analysis ?? emptyPatternAnalysis;
  const signal = stats.signal_integrity ?? emptySignalIntegrity;
  const concurrencyLimit = Math.max(safety.concurrency_limit, 1);
  const dailyLimit = Math.max(safety.daily_limit, 1);

  const behavioralMetrics = [
    {
      label: "Confusion Rate",
      value: `${behavior.intervention_confusion_rate.toFixed(1)}%`,
      sub: `${behavior.confusion_signal_count} signals`,
      icon: AlertCircle,
      color: "text-red-400",
    },
    {
      label: "Explainability Use",
      value: `${behavior.explainability.explanation_to_recovery_rate.toFixed(1)}%`,
      sub: `${behavior.explainability.recovery_hint_actions}/${behavior.explainability.supervisor_opens} hint actions`,
      icon: Brain,
      color: "text-blue-400",
    },
    {
      label: "Escalation Success",
      value: `${behavior.human_escalation.success_rate.toFixed(1)}%`,
      sub: `${behavior.human_escalation.resolved} resolved`,
      icon: UserCheck,
      color: "text-green-400",
    },
    {
      label: "Replay Success",
      value: `${behavior.replay.success_rate.toFixed(1)}%`,
      sub: `${behavior.replay.successes}/${behavior.replay.attempts} replays`,
      icon: RotateCcw,
      color: "text-amber-400",
    },
    {
      label: "Trust Retention",
      value: `${behavior.trust_retention.retention_rate.toFixed(1)}%`,
      sub: `${behavior.trust_retention.continuation_actions} continued`,
      icon: TrendingUp,
      color: "text-teal-400",
    },
  ];

  const metrics = [
    { 
      label: "Workflow Completion", 
      value: `${stats.slo.completion_rate.toFixed(1)}%`, 
      sub: "Target: >95%",
      icon: ShieldCheck, 
      color: "text-green-400" 
    },
    { 
      label: "Recovery Success", 
      value: `${stats.slo.recovery_success_rate.toFixed(1)}%`, 
      sub: "Checkpoint Reliability",
      icon: Zap, 
      color: "text-blue-400" 
    },
    { 
      label: "Intervention Rate", 
      value: `${stats.slo.intervention_frequency.toFixed(2)}`, 
      sub: "Human effort per app",
      icon: Users, 
      color: "text-teal-400" 
    },
    { 
      label: "Mean Node Latency", 
      value: `${(stats.slo.mean_node_duration_ms / 1000).toFixed(2)}s`, 
      sub: "Orchestration Speed",
      icon: Timer, 
      color: "text-amber-400" 
    },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header>
        <div className="flex items-center gap-3 mb-2">
          <Activity className="text-blue-500" />
          <h1 className="text-3xl font-black tracking-tight text-white uppercase">Behavioral Systems Validation</h1>
        </div>
        <p className="text-slate-400">Phase 24 signals for how humans recover, trust, and collaborate with orchestration.</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-6">
        {behavioralMetrics.map((m, i) => (
          <div key={m.label} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-2xl bg-slate-950 border border-slate-800 ${m.color}`}>
                <m.icon size={20} />
              </div>
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Phase 24.{i+1}</span>
            </div>
            <h3 className="text-3xl font-black text-white mb-1">{m.value}</h3>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-tight">{m.label}</p>
            <p className="text-[10px] text-slate-600 mt-3 font-mono">{m.sub}</p>
          </div>
        ))}
      </div>

      <section className="space-y-6">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-2xl font-black uppercase tracking-tight text-white">Signal Validation And Noise Reduction</h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{signal.guardrails.note}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={`rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-widest ${confidenceColor(signal.summary.overall_confidence)}`}>
                {signal.summary.overall_confidence}
              </span>
              <span className={`rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-widest ${confidenceColor(signal.summary.optimization_readiness)}`}>
                {signal.summary.optimization_readiness.replace(/_/g, " ")}
              </span>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              ["Sample Confidence", signal.sample_quality.overall_confidence, signal.sample_quality.interpretation],
              ["Temporal Stability", signal.temporal_stability.overall_stability, signal.temporal_stability.interpretation],
              ["Causation Guards", `${signal.summary.causation_guard_count}`, "Active confounder checks"],
              ["Stale Signal Share", `${signal.signal_decay.stale_signal_share.toFixed(1)}%`, signal.signal_decay.interpretation],
            ].map(([label, value, sub]) => (
              <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</p>
                <p className="mt-2 text-2xl font-black capitalize text-white">{value}</p>
                <p className="mt-2 text-xs leading-relaxed text-slate-500">{sub}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Shield size={20} className="text-blue-400" />
              Sample Quality
            </h3>
            {signal.sample_quality.metric_samples.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No sample quality data yet.
              </div>
            ) : (
              <div className="space-y-3">
                {signal.sample_quality.metric_samples.map((metric) => (
                  <div key={metric.metric} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-black uppercase tracking-wider text-white">{metric.metric.replace(/_/g, " ")}</p>
                        <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">{metric.actionability.replace(/_/g, " ")}</p>
                      </div>
                      <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(metric.confidence)}`}>
                        {metric.confidence.replace(/_/g, " ")}
                      </span>
                    </div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full bg-blue-400"
                        style={{ width: `${Math.min((metric.sample_size / Math.max(metric.minimum_for_stable, 1)) * 100, 100)}%` }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-slate-500">{metric.sample_size} samples / {metric.minimum_for_stable} stable target</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Timer size={20} className="text-amber-400" />
              Temporal Stability
            </h3>
            {signal.temporal_stability.comparisons.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No temporal comparison yet.
              </div>
            ) : (
              <div className="space-y-3">
                {signal.temporal_stability.comparisons.map((item) => (
                  <div key={item.metric} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-black uppercase tracking-wider text-white">{item.metric.replace(/_/g, " ")}</p>
                      <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(item.stability)}`}>
                        {item.stability}
                      </span>
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2">
                      {[
                        ["Recent", item.recent],
                        ["Baseline", item.baseline],
                        ["Delta", item.delta],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                          <p className="text-sm font-black text-white">{Number(value).toFixed(1)}%</p>
                          <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <AlertCircle size={20} className="text-red-400" />
              Causation Guards
            </h3>
            {signal.causation_guards.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No causation guards triggered.
              </div>
            ) : (
              <div className="space-y-3">
                {signal.causation_guards.map((guard) => (
                  <div key={`${guard.signal}-${guard.possible_confounder}`} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-sm font-black uppercase tracking-wider text-white">{guard.signal.replace(/_/g, " ")}</p>
                      <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(guard.confidence)}`}>
                        {guard.confidence}
                      </span>
                    </div>
                    <p className={`text-xs font-black uppercase tracking-widest ${riskColor(guard.severity)}`}>{guard.possible_confounder.replace(/_/g, " ")}</p>
                    <p className="mt-2 text-xs leading-relaxed text-slate-500">{guard.guardrail}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Users size={20} className="text-teal-400" />
              Segment Context
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Segment", signal.segment_analysis.current_user_segment.replace(/_/g, " ")],
                ["Interventions / Workflow", signal.segment_analysis.interventions_per_workflow.toFixed(2)],
                ["Replays", signal.segment_analysis.replays],
                ["Terminations", signal.segment_analysis.terminations],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <p className="text-lg font-black capitalize text-white">{value}</p>
                  <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {signal.segment_analysis.behavior_flags.map((flag) => (
                <span key={flag} className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-slate-300">
                  {flag.replace(/_/g, " ")}
                </span>
              ))}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">{signal.segment_analysis.aggregate_caveat}</p>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <TrendingUp size={20} className="text-green-400" />
              Signal Decay
            </h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Half Life", `${signal.signal_decay.half_life_days}d`],
                ["Workflow Weight", `${signal.signal_decay.decayed_workflow_weight}/${signal.signal_decay.raw_workflows}`],
                ["Event Weight", `${signal.signal_decay.decayed_event_weight}/${signal.signal_decay.raw_events}`],
                ["Stale Share", `${signal.signal_decay.stale_signal_share.toFixed(1)}%`],
              ].map(([label, value]) => (
                <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <p className="text-lg font-black text-white">{value}</p>
                  <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-xs leading-relaxed text-slate-500">{signal.signal_decay.interpretation}</p>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/50 p-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-black uppercase tracking-tight text-white">Operational Pattern Analysis</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-400">{pattern.analysis_guardrails.note}</p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              ["Workflows", pattern.sample.workflows],
              ["Steps", pattern.sample.steps],
              ["Events", pattern.sample.events],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3">
                <p className="text-xl font-black text-white">{value}</p>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          {[
            {
              label: "Top Confusion Node",
              value: pattern.summary.top_confusion_node?.replace(/_/g, " ") || "No signal",
              confidence: pattern.summary.top_confusion_node_confidence,
            },
            {
              label: "Highest Friction ATS",
              value: pattern.summary.highest_friction_platform || "No signal",
              confidence: pattern.summary.highest_friction_platform_confidence,
            },
            {
              label: "Intervention Fatigue",
              value: pattern.summary.fatigue_risk_level,
              confidence: pattern.intervention_fatigue.confidence,
              risk: pattern.summary.fatigue_risk_level,
            },
            {
              label: "Trust Decay",
              value: pattern.summary.trust_decay_risk_level,
              confidence: pattern.trust_decay.confidence,
              risk: pattern.summary.trust_decay_risk_level,
            },
          ].map((item) => (
            <div key={item.label} className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
              <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">{item.label}</p>
              <p className={`text-2xl font-black capitalize ${item.risk ? riskColor(item.risk) : "text-white"}`}>{item.value}</p>
              <span className={`mt-4 inline-flex rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-widest ${confidenceColor(item.confidence)}`}>
                {item.confidence}
              </span>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Flag size={20} className="text-red-400" />
              Node Friction Patterns
            </h3>
            {pattern.node_patterns.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No node patterns observed yet.
              </div>
            ) : (
              <div className="space-y-4">
                {pattern.node_patterns.map((node) => (
                  <div key={node.step_name} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="mb-3 flex items-start justify-between gap-4">
                      <div>
                        <p className="font-black uppercase tracking-wider text-white">{node.step_name.replace(/_/g, " ")}</p>
                        <p className="mt-1 text-xs leading-relaxed text-slate-500">{node.recommended_review}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-black text-red-400">{node.friction_score.toFixed(1)}</p>
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(node.confidence)}`}>
                          {node.confidence}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
                      {[
                        ["Replay", node.replay_rate],
                        ["Terminate", node.termination_rate],
                        ["Report", node.report_rate],
                        ["Retry", node.retry_rate],
                        ["Escalate", node.escalation_rate],
                      ].map(([label, value]) => (
                        <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                          <p className="text-sm font-black text-white">{Number(value).toFixed(1)}%</p>
                          <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Brain size={20} className="text-blue-400" />
              Explanation Effectiveness
            </h3>
            {pattern.explanation_patterns.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No explanation patterns observed yet.
              </div>
            ) : (
              <div className="space-y-4">
                {pattern.explanation_patterns.map((item) => (
                  <div key={item.step_name} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-black uppercase tracking-wider text-white">{item.step_name.replace(/_/g, " ")}</p>
                        <p className="mt-1 text-xs leading-relaxed text-slate-500">{item.interpretation}</p>
                      </div>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(item.confidence)}`}>
                        {item.confidence}
                      </span>
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-2">
                      <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                        <p className="text-sm font-black text-white">{item.views}</p>
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Views</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                        <p className="text-sm font-black text-white">{item.hint_actions}</p>
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Actions</p>
                      </div>
                      <div className="rounded-xl border border-slate-800 bg-slate-900 p-3">
                        <p className="text-sm font-black text-blue-400">{item.hint_action_rate.toFixed(1)}%</p>
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Action Rate</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8 xl:col-span-2">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <BarChart3 size={20} className="text-teal-400" />
              ATS Friction
            </h3>
            {pattern.ats_friction.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
                No ATS friction patterns observed yet.
              </div>
            ) : (
              <div className="space-y-3">
                {pattern.ats_friction.map((platform) => (
                  <div key={platform.platform} className="grid grid-cols-2 gap-3 rounded-2xl border border-slate-800 bg-slate-950 p-4 md:grid-cols-6">
                    <div className="col-span-2">
                      <p className="font-black text-white">{platform.platform}</p>
                      <span className={`mt-2 inline-flex rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${confidenceColor(platform.confidence)}`}>
                        {platform.confidence}
                      </span>
                    </div>
                    {[
                      ["Friction", platform.friction_score],
                      ["Complete", platform.completion_rate],
                      ["Fail", platform.failure_rate],
                      ["Interventions", platform.interventions_per_workflow],
                    ].map(([label, value]) => (
                      <div key={label}>
                        <p className="text-sm font-black text-white">{typeof value === "number" ? value.toFixed(label === "Interventions" ? 2 : 1) : value}</p>
                        <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">{label}</p>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-8">
            <h3 className="mb-6 flex items-center gap-2 text-xl font-bold text-white">
              <Users size={20} className="text-amber-400" />
              Fatigue And Trust
            </h3>
            <div className="space-y-4">
              {[
                ["Fatigue Risk", pattern.intervention_fatigue.risk_level, riskColor(pattern.intervention_fatigue.risk_level)],
                ["Trust Decay Risk", pattern.trust_decay.risk_level, riskColor(pattern.trust_decay.risk_level)],
                ["Escalations / Workflow", pattern.intervention_fatigue.interventions_per_workflow.toFixed(2), "text-white"],
                ["Escalations / Success", pattern.intervention_fatigue.interventions_per_successful_application.toFixed(2), "text-white"],
                ["Failed Recoveries Before Termination", pattern.trust_decay.average_failed_recoveries_before_termination.toFixed(2), "text-white"],
              ].map(([label, value, color]) => (
                <div key={label} className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-sm text-slate-400">{label}</span>
                  <span className={`text-lg font-black capitalize ${color}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Primary SLO Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {metrics.map((m, i) => (
          <div key={i} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-2xl bg-slate-950 border border-slate-800 ${m.color}`}>
                <m.icon size={20} />
              </div>
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-600">Metric 0{i+1}</span>
            </div>
            <h3 className="text-3xl font-black text-white mb-1">{m.value}</h3>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-tight">{m.label}</p>
            <p className="text-[10px] text-slate-600 mt-3 font-mono">{m.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-12">
        {/* Throughput Monitor */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <BarChart3 size={20} className="text-slate-400" />
            Orchestration Throughput
          </h3>
          <div className="space-y-6">
            <div className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
              <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">Active Concurrency</span>
              <span className="text-2xl font-black text-blue-400">{stats.throughput.total_active_workflows}</span>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate-950 rounded-2xl border border-slate-800">
              <span className="text-sm font-bold text-slate-400 uppercase tracking-widest">Total Nodes Executed</span>
              <span className="text-2xl font-black text-white">{stats.throughput.total_nodes_executed}</span>
            </div>
          </div>
        </div>

        {/* Scaling Guards */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <AlertCircle size={20} className="text-amber-400" />
            Operational Capacity Guards
          </h3>
          <div className="p-6 bg-amber-500/5 border border-amber-500/20 rounded-2xl space-y-5">
            <p className="text-sm text-amber-200/70 leading-relaxed mb-4">
              Concurrency is currently capped at <span className="text-amber-400 font-bold">{safety.concurrency_limit} simultaneous workflows</span> for beta validation.
            </p>
            <div>
              <div className="mb-2 flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-500">
                <span>Concurrency</span>
                <span>{safety.active_workflows}/{safety.concurrency_limit}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-amber-400 h-full transition-all duration-1000"
                  style={{ width: `${Math.min((safety.active_workflows / concurrencyLimit) * 100, 100)}%` }}
                />
              </div>
            </div>
            <div>
              <div className="mb-2 flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-500">
                <span>Daily automation</span>
                <span>{safety.daily_started}/{safety.daily_limit}</span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div
                  className="bg-blue-400 h-full transition-all duration-1000"
                  style={{ width: `${Math.min((safety.daily_started / dailyLimit) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Shield size={20} className="text-green-400" />
            Beta Trust Signals
          </h3>
          <div className="space-y-4">
            {[
              ["Onboarding completed", betaObservability.onboarding_completions],
              ["Trace exports", betaObservability.trace_exports],
              ["Reported nodes", betaObservability.reported_nodes],
              ["Repeated corrections", betaObservability.repeated_user_corrections],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between border-b border-slate-800 pb-3">
                <span className="text-sm text-slate-400">{label}</span>
                <span className="text-lg font-black text-white">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Users size={20} className="text-teal-400" />
            Intervention Queue
          </h3>
          <div className="space-y-5">
            <div>
              <p className="text-3xl font-black text-white">{betaObservability.active_interventions}</p>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Waiting for user action</p>
            </div>
            <div>
              <p className="text-3xl font-black text-amber-400">{betaObservability.stale_interventions}</p>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Older than 24 hours</p>
            </div>
            <div>
              <p className="text-3xl font-black text-blue-400">
                {(betaObservability.approval_latency_ms / 1000).toFixed(1)}s
              </p>
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Mean approval latency</p>
            </div>
          </div>
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Flag size={20} className="text-red-400" />
            Confusion Points
          </h3>
          {betaObservability.confusion_points.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
              No reported nodes yet.
            </div>
          ) : (
            <div className="space-y-3">
              {betaObservability.confusion_points.map((point) => (
                <div key={point.step_name} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <span className="text-sm font-bold text-slate-300">{point.step_name.replace(/_/g, " ")}</span>
                  <span className="text-sm font-black text-red-400">{point.reports}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <RotateCcw size={20} className="text-amber-400" />
            Replay Outcome Quality
          </h3>
          {behavior.replay.outcomes_by_step.length === 0 ? (
            <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
              No checkpoint replays observed yet.
            </div>
          ) : (
            <div className="space-y-3">
              {behavior.replay.outcomes_by_step.map((item) => (
                <div key={item.outcome} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <span className="text-sm font-bold text-slate-300">{item.outcome.replace(/_/g, " ").replace(":", " / ")}</span>
                  <span className="text-sm font-black text-amber-400">{item.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <AlertCircle size={20} className="text-red-400" />
            Termination Analysis
          </h3>
          {behavior.termination.count === 0 ? (
            <div className="rounded-2xl border border-slate-800 border-dashed p-8 text-center text-sm text-slate-500">
              No user terminations observed yet.
            </div>
          ) : (
            <div className="space-y-6">
              <div className="space-y-3">
                {behavior.termination.reasons.map((item) => (
                  <div key={item.reason} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <span className="text-sm font-bold text-slate-300">{item.reason.replace(/_/g, " ")}</span>
                    <span className="text-sm font-black text-red-400">{item.count}</span>
                  </div>
                ))}
              </div>
              {behavior.termination.by_step.length > 0 && (
                <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                  <p className="mb-3 text-[10px] font-black uppercase tracking-widest text-slate-500">Active nodes at termination</p>
                  <div className="space-y-2">
                    {behavior.termination.by_step.map((item) => (
                      <div key={item.step_name} className="flex items-center justify-between text-sm">
                        <span className="font-bold text-slate-300">{item.step_name.replace(/_/g, " ")}</span>
                        <span className="font-black text-slate-500">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
