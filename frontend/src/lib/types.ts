export type JobStatus =
  | "SCRAPED"
  | "ANALYSIS_PENDING"
  | "ANALYZING"
  | "ANALYZED"
  | "ANALYSIS_FAILED"
  | "SHORTLISTED"
  | "READY_TO_APPLY"
  | "APPLYING"
  | "APPLYING_PENDING_APPROVAL"
  | "APPLIED"
  | "FAILED"
  | "INTERVIEW"
  | "REJECTED";

export interface AiAnalysis {
  justification?: string;
  [key: string]: unknown;
}

export interface Job {
  id: number;
  source_id: string;
  title: string;
  company: string;
  location?: string | null;
  description?: string | null;
  salary?: string | null;
  url: string;
  source: string;
  remote_type?: string | null;
  status: JobStatus;
  ai_score?: number | null;
  ai_analysis?: AiAnalysis | null;
  analysis_attempts?: number;
  analysis_error?: string | null;
  last_analysis_model?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface JobListParams {
  skip?: number;
  limit?: number;
  status?: JobStatus;
  source?: string;
  location?: string;
  remote_type?: string;
  search?: string;
  min_score?: number;
  max_score?: number;
  sort?: "quality" | "score" | "newest" | "source" | "company";
}

export interface JobSourceSummary {
  source: string;
  count: number;
  supported: boolean;
}

export interface Resume {
  id: number;
  profile_id?: number;
  name: string;
  content_text?: string;
  file_path?: string | null;
  version: number;
  is_base: boolean;
  is_optimized?: boolean;
  parent_id?: number | null;
  extraction_status: string;
  extraction_data?: Record<string, unknown> | null;
  confidence_scores?: Record<string, number> | null;
  review_status?: string;
  created_at: string;
  updated_at?: string | null;
}

export interface ProfileData {
  id?: number;
  user_id?: number;
  full_name?: string | null;
  title?: string | null;
  experience_years?: number | null;
  skills?: string[];
  tech_stack?: Record<string, string[]>;
  preferred_roles?: string[];
  preferred_locations?: string[];
  remote_preference?: string;
  salary_expectation?: number | null;
  preferred_currency?: string;
  work_authorization?: string | null;
  bio?: string | null;
  locked_fields?: string[];
  resumes?: Resume[];
  salary_multi_currency?: Record<string, number>;
  created_at?: string;
  updated_at?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

export interface UserAccount {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface TelemetryEvent {
  event_id?: string;
  type: string;
  category?: string;
  payload: unknown;
  resource_id?: string;
  timestamp: string;
}

export interface IntelligenceInsight {
  type: string;
  severity: "success" | "warning" | "info" | string;
  message: string;
  action: string;
}

export interface SourcePerformance {
  source: string;
  total_apps: number;
  interviews: number;
  conversion_rate: number;
}

export interface ScoreCorrelation {
  range: string;
  total: number;
  interviews: number;
  rate: number;
}

export interface ResumePerformance {
  resume_id: number | null;
  total_apps: number;
  interviews: number;
  success_rate: number;
}

export interface IntelligenceStats {
  source_performance: SourcePerformance[];
  score_correlation: ScoreCorrelation[];
  resume_performance: ResumePerformance[];
  actionable_insights: IntelligenceInsight[];
  governed_recommendations?: GovernedRecommendationIntelligence;
}

export interface OperationsStats {
  slo: {
    completion_rate: number;
    recovery_success_rate: number;
    intervention_frequency: number;
    mean_node_duration_ms: number;
  };
  throughput: {
    total_active_workflows: number;
    total_nodes_executed: number;
  };
  safety: {
    daily_started: number;
    daily_limit: number;
    daily_remaining: number;
    active_workflows: number;
    concurrency_limit: number;
    concurrency_remaining: number;
  };
  beta_observability: {
    onboarding_completions: number;
    active_interventions: number;
    stale_interventions: number;
    approval_latency_ms: number;
    reported_nodes: number;
    trace_exports: number;
    repeated_user_corrections: number;
    confusion_points: Array<{
      step_name: string;
      reports: number;
    }>;
  };
  behavioral_validation: {
    intervention_confusion_rate: number;
    confusion_signal_count: number;
    explainability: {
      supervisor_opens: number;
      recovery_hint_actions: number;
      explanation_to_recovery_rate: number;
    };
    human_escalation: {
      resolved: number;
      pending: number;
      failed: number;
      success_rate: number;
    };
    replay: {
      attempts: number;
      successes: number;
      loops: number;
      success_rate: number;
      outcomes_by_step: Array<{
        outcome: string;
        count: number;
      }>;
    };
    termination: {
      count: number;
      reasons: Array<{
        reason: string;
        count: number;
      }>;
      by_step: Array<{
        step_name: string;
        count: number;
      }>;
    };
    trust_retention: {
      continuation_actions: number;
      termination_actions: number;
      retention_rate: number;
    };
  };
  pattern_analysis: {
    analysis_guardrails: {
      directional_sample_size: number;
      stable_sample_size: number;
      note: string;
    };
    node_patterns: Array<{
      step_name: string;
      observations: number;
      confidence: "insufficient" | "directional" | "stable" | string;
      friction_score: number;
      replay_rate: number;
      termination_rate: number;
      report_rate: number;
      retry_rate: number;
      escalation_rate: number;
      counts: Record<string, number>;
      recommended_review: string;
    }>;
    explanation_patterns: Array<{
      step_name: string;
      views: number;
      hint_actions: number;
      hint_action_rate: number;
      confidence: "insufficient" | "directional" | "stable" | string;
      interpretation: string;
    }>;
    ats_friction: Array<{
      platform: string;
      workflows: number;
      confidence: "insufficient" | "directional" | "stable" | string;
      friction_score: number;
      completion_rate: number;
      failure_rate: number;
      interventions_per_workflow: number;
      replays_per_workflow: number;
      reports_per_workflow: number;
      terminations_per_workflow: number;
    }>;
    intervention_fatigue: {
      total_interventions: number;
      interventions_per_workflow: number;
      interventions_per_successful_application: number;
      high_fatigue_workflows: number;
      confidence: "insufficient" | "directional" | "stable" | string;
      risk_level: "unknown" | "low" | "medium" | "high" | string;
    };
    trust_decay: {
      terminated_workflows: number;
      termination_rate: number;
      average_failed_recoveries_before_termination: number;
      confidence: "insufficient" | "directional" | "stable" | string;
      risk_level: "unknown" | "low" | "medium" | "high" | string;
    };
    summary: {
      top_confusion_node?: string | null;
      top_confusion_node_confidence: string;
      highest_friction_platform?: string | null;
      highest_friction_platform_confidence: string;
      fatigue_risk_level: string;
      trust_decay_risk_level: string;
    };
    sample: {
      workflows: number;
      steps: number;
      events: number;
      confidence: "insufficient" | "directional" | "stable" | string;
    };
  };
  signal_integrity: {
    guardrails: {
      note: string;
      minimums: {
        observe: number;
        directional: number;
        stable: number;
      };
      temporal_windows_days: {
        recent: number;
        baseline: number;
      };
      decay_half_life_days: number;
    };
    sample_quality: {
      overall_confidence: "insufficient" | "observe_only" | "directional" | "stable" | string;
      workflows: number;
      steps: number;
      events: number;
      metric_samples: Array<{
        metric: string;
        sample_size: number;
        confidence: "insufficient" | "observe_only" | "directional" | "stable" | string;
        minimum_for_directional: number;
        minimum_for_stable: number;
        actionability: string;
      }>;
      platform_coverage: Array<{
        platform: string;
        workflows: number;
        confidence: "insufficient" | "observe_only" | "directional" | "stable" | string;
      }>;
      interpretation: string;
    };
    temporal_stability: {
      recent_window_days: number;
      baseline_window_days: number;
      recent_samples: number;
      baseline_samples: number;
      comparisons: Array<{
        metric: string;
        recent: number;
        baseline: number;
        delta: number;
        stability: "insufficient" | "stable" | "drifting" | "volatile" | string;
      }>;
      overall_stability: "insufficient" | "stable" | "drifting" | "volatile" | string;
      interpretation: string;
    };
    causation_guards: Array<{
      signal: string;
      possible_confounder: string;
      severity: "low" | "medium" | "high" | string;
      confidence: string;
      guardrail: string;
    }>;
    segment_analysis: {
      current_user_segment: string;
      behavior_flags: string[];
      workflows: number;
      interventions_per_workflow: number;
      replays: number;
      reports: number;
      terminations: number;
      aggregate_caveat: string;
    };
    signal_decay: {
      half_life_days: number;
      raw_workflows: number;
      decayed_workflow_weight: number;
      raw_events: number;
      decayed_event_weight: number;
      stale_signal_share: number;
      interpretation: string;
    };
    summary: {
      optimization_readiness: "observe_only" | "human_review_only" | "review_eligible" | string;
      overall_confidence: string;
      temporal_stability: string;
      causation_guard_count: number;
      stale_signal_share: number;
    };
  };
  governance: GovernanceStats;
  supportability: SupportabilityStats;
  reliability_scaling: ReliabilityScalingStats;
  orchestration_compression?: OrchestrationCompressionStats;
  reliability_optimization?: ReliabilityOptimizationStats;
}

export interface GovernanceRecommendation {
  id: number;
  source_signal: string;
  recommendation_type: string;
  title: string;
  rationale: string;
  target_policy: string;
  proposed_change: Record<string, unknown>;
  rollback_plan: Record<string, unknown>;
  explainability: {
    confidence_level?: string;
    sample_size?: {
      workflows?: number;
      steps?: number;
      events?: number;
    };
    temporal_stability?: string;
    confounder_warnings?: Array<Record<string, unknown>>;
    user_segment_scope?: Record<string, unknown>;
    decay_weight?: Record<string, unknown>;
  };
  shadow_evaluation: Record<string, unknown>;
  status: string;
  reviewer_id?: number | null;
  decision_note?: string | null;
  created_at?: string | null;
  approved_at?: string | null;
  rolled_back_at?: string | null;
}

export interface GovernanceStats {
  review_queue: GovernanceRecommendation[];
  timeline: Array<{
    id: number;
    recommendation_id: number;
    actor_user_id?: number | null;
    action: string;
    reason?: string | null;
    before_state?: Record<string, unknown> | null;
    after_state?: Record<string, unknown> | null;
    outcome_metrics?: Record<string, unknown> | null;
    created_at?: string | null;
  }>;
  metrics: {
    recommendation_acceptance_rate: number;
    rollback_frequency: number;
    policy_drift_rate: number;
    false_recommendation_rate: number;
    human_override_frequency: number;
    pending_reviews: number;
  };
  guardrails: {
    note: string;
    approval_required_for: string[];
    shadow_modes: string[];
  };
}

export interface SupportabilityStats {
  incident_console: Array<{
    workflow_id: number;
    job_id?: number | null;
    platform: string;
    status: string;
    active_step?: string | null;
    classification: string;
    severity: string;
    escalation_history: number;
    retry_history: number;
    trace_event_count: number;
    available_actions: string[];
    created_at?: string | null;
  }>;
  trace_explorer: Array<Record<string, unknown>>;
  classification: {
    categories: Array<{
      classification: string;
      count: number;
    }>;
    supported_classes: string[];
  };
  recovery_recommendations: Array<{
    workflow_id: number;
    classification: string;
    recommended_action: string;
    mutation_allowed: boolean;
    reason: string;
  }>;
  cross_layer_correlation: Record<string, number>;
  metrics: {
    mean_recovery_time_seconds: number;
    replay_recovery_success: number;
    incident_recurrence_rate: number;
    support_escalation_volume: number;
    ats_drift_detection_speed_minutes: number;
    open_incidents: number;
  };
}

export interface ReliabilityScalingStats {
  horizontal_worker_orchestration: {
    distributed_worker_pools: Array<{
      queue: string;
      platform: string;
      workload: number;
      active: number;
      isolation: string;
    }>;
    browser_resource_scheduling: {
      policy: string;
      active_workflows: number;
      risk: string;
    };
  };
  durable_redundancy: Record<string, string>;
  security_secret_governance: Record<string, unknown>;
  observability_stack: Record<string, unknown>;
  chaos_testing: {
    scenarios: string[];
    last_result: string;
  };
  cost_capacity: {
    browser_cost_per_workflow_units: number;
    orchestration_resource_usage_units: number;
    replay_overhead: number;
    ats_operational_cost: Array<{
      platform: string;
      cost_units: number;
    }>;
    worker_saturation_threshold: string;
  };
  slos: Record<string, {
    actual: number;
    target: number;
    met: boolean;
  }>;
}

export interface OrchestrationCompressionStats {
  primitive_registry: {
    version: string;
    total_primitives: number;
    primitives: Array<Record<string, unknown>>;
    step_mapping: Record<string, string>;
  };
  state_surface: {
    hierarchy: Record<string, unknown>;
    workflow_status_map: Record<string, unknown>;
    job_status_map: Record<string, unknown>;
    active_state_counts: Array<{
      state: string;
      count: number;
    }>;
    unique_canonical_states: number;
  };
  event_taxonomy: {
    categories: Array<{
      category: string;
      count: number;
    }>;
    top_events: Array<{
      event_type: string;
      count: number;
    }>;
    validation_warnings: Array<Record<string, unknown>>;
    retention_policies: Array<Record<string, unknown>>;
    compression: Record<string, unknown>;
  };
  escalation_templates: Array<Record<string, unknown>>;
  recovery_paths: {
    available_actions: string[];
    recommendations: Array<Record<string, unknown>>;
    action_distribution: Array<{
      action: string;
      count: number;
    }>;
    mean_confidence: number;
    safety_validated: number;
  };
  complexity_dashboard: {
    unique_workflow_states: number;
    unique_step_states: number;
    avg_workflow_branching: number;
    max_workflow_branching: number;
    escalation_density: number;
    replay_loop_rate: number;
    state_transition_entropy: number;
    event_volume_growth: number;
    primitive_reuse_ratio: number;
  };
  guardrails: Record<string, unknown>;
}

export interface ReliabilityOptimizationStats {
  browser_resource_scheduler: {
    memory_usage_mb_estimate: number;
    browser_lifetime_policy: Record<string, unknown>;
    tab_saturation_percent: number;
    ats_resource_cost: Array<Record<string, unknown>>;
    adaptive_concurrency: {
      current_active: number;
      recommended_new_capacity: number;
      crash_risk: string;
    };
    pooling_policy: string;
  };
  adaptive_queue_prioritization: {
    policy: string;
    starvation_prevention: string;
    queues: Array<{
      workflow_id: number;
      platform: string;
      status: string;
      priority_score: number;
      priority_reasons: string[];
    }>;
  };
  reliability_scoring_v2: {
    node_stability: Array<Record<string, unknown>>;
    ats_reliability: Array<Record<string, unknown>>;
    fragility_prediction: {
      risk_score: number;
      level: string;
      weakest_node?: Record<string, unknown> | null;
      weakest_ats?: Record<string, unknown> | null;
    };
  };
  replay_optimization: {
    replay_latency_ms: number;
    replay_path_cache_candidates: Array<Record<string, unknown>>;
    redundant_navigation_count: number;
    browser_warm_state_reuse: string;
    checkpoint_hydration_speed: string;
    deterministic_replay_tracing: number;
    replay_divergence_detection: {
      divergent_replays: number;
      rate: number;
    };
  };
  intervention_cost: {
    minutes_per_escalation: number;
    approvals_per_workflow: number;
    replay_fatigue: number;
    intervention_abandonment: number;
    estimated_human_cost_minutes: number;
  };
  workflow_throughput: {
    workflow_completion_duration_seconds: number;
    completed_workflows: number;
    active_workflows: number;
    queued_workflows: number;
    node_bottlenecks: Array<Record<string, unknown>>;
    queue_pressure: number;
    concurrency_saturation: number;
  };
  guardrails: Record<string, unknown>;
}

export interface GovernedRecommendation {
  type: string;
  target: string;
  confidence: string;
  sample_quality: string;
  sample_size: number;
  temporal_stability: string;
  causation_warning: string;
  rollback_safety: string;
  message: string;
  recommended_action: string;
  raw_score: number;
  authority: string;
  automatic_mutation_allowed: boolean;
  [key: string]: unknown;
}

export interface GovernedRecommendationIntelligence {
  workflow_confidence: {
    overall: string;
    platforms: GovernedRecommendation[];
    factors: Record<string, unknown>;
  };
  resume_variant_recommendations: GovernedRecommendation[];
  ats_strategy: GovernedRecommendation[];
  guided_recovery: GovernedRecommendation[];
  trust_profiles: {
    current_profile: string;
    available_profiles: Array<Record<string, unknown>>;
    signals: Record<string, unknown>;
  };
  recommendation_governance: Record<string, unknown>;
}

export interface WorkflowStepExplanation {
  label: string;
  status_text: string;
  canonical_state?: {
    state: string;
    leaf: string;
  };
  autonomy: "autonomous" | "supervised" | "approval_required" | string;
  summary: string;
  why: string;
  data_used: string[];
  checkpoint: string;
  risk_level: "low" | "medium" | "high" | string;
  recovery_hint?: string | null;
  next_action: {
    type: "retry" | "approve" | "wait" | "none" | string;
    label?: string | null;
  };
  primitive?: Record<string, unknown> | null;
  escalation?: Record<string, unknown> | null;
  recovery_recommendation?: Record<string, unknown> | null;
}

export interface WorkflowStep {
  id: number;
  name: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED" | "PAUSED_FOR_HUMAN" | "SKIPPED";
  attempts: number;
  error?: string;
  duration?: number;
  started_at?: string;
  completed_at?: string | null;
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  explanation?: WorkflowStepExplanation;
}

export interface WorkflowDetails {
  workflow: {
    id?: number;
    platform: string;
    status?: string;
    job_id?: number;
    created_at?: string | null;
    updated_at?: string | null;
    summary?: {
      headline: string;
      status_text: string;
      canonical_state?: {
        state: string;
        leaf: string;
      };
      active_step_id?: number | null;
      active_step_name?: string | null;
      completed_steps: number;
      total_steps: number;
      progress_percent: number;
      autonomy_boundary: string;
    };
  };
  steps: WorkflowStep[];
}

export interface WorkflowTrace extends WorkflowDetails {
  timeline: TelemetryEvent[];
}
