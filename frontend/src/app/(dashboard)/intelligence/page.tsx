"use client";

import { useQuery } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import {
  TrendingUp,
  Target,
  Award,
  AlertTriangle,
  Lightbulb,
  BarChart3,
  Zap,
  ShieldCheck,
  RotateCcw,
} from "lucide-react";
import type { IntelligenceInsight, IntelligenceStats } from "@/lib/types";

const emptyStats: IntelligenceStats = {
  actionable_insights: [],
  source_performance: [],
  score_correlation: [],
  resume_performance: [],
  governed_recommendations: {
    workflow_confidence: {
      overall: "low_confidence",
      platforms: [],
      factors: {},
    },
    resume_variant_recommendations: [],
    ats_strategy: [],
    guided_recovery: [],
    trust_profiles: {
      current_profile: "standard",
      available_profiles: [],
      signals: {},
    },
    recommendation_governance: {},
  },
};

const getInsightStyle = (severity: IntelligenceInsight["severity"]) => {
  if (severity === "success") return "bg-green-500/5 border-green-500/20";
  if (severity === "warning") return "bg-amber-500/5 border-amber-500/20";
  return "bg-blue-500/5 border-blue-500/20";
};

const getInsightIconStyle = (severity: IntelligenceInsight["severity"]) => {
  if (severity === "success") return "bg-green-500/20 text-green-400";
  if (severity === "warning") return "bg-amber-500/20 text-amber-400";
  return "bg-blue-500/20 text-blue-400";
};

const getConfidenceStyle = (confidence: string) => {
  if (confidence === "high_confidence") return "text-green-400 border-green-500/20 bg-green-500/10";
  if (confidence === "medium_confidence") return "text-amber-400 border-amber-500/20 bg-amber-500/10";
  return "text-blue-400 border-blue-500/20 bg-blue-500/10";
};

export default function IntelligenceCenter() {
  const { data = emptyStats, isLoading } = useQuery<IntelligenceStats>({
    queryKey: ["intelligence_stats"],
    queryFn: () => backendApi.intelligence.stats(),
  });

  if (isLoading) return <div className="p-8 text-slate-500 animate-pulse">Calculating operational intelligence...</div>;

  const governed = data.governed_recommendations ?? emptyStats.governed_recommendations!;
  const topResume = governed.resume_variant_recommendations[0];
  const topAts = governed.ats_strategy[0];

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-black tracking-tight text-white mb-2">INTELLIGENCE CENTER</h1>
        <p className="text-slate-400">Operational decision support and strategy optimization.</p>
      </header>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 className="flex items-center gap-2 text-lg font-black uppercase tracking-tight text-white">
              <ShieldCheck size={20} className="text-green-400" />
              Workflow Confidence
            </h2>
            <span className={`rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-widest ${getConfidenceStyle(governed.workflow_confidence.overall)}`}>
              {governed.workflow_confidence.overall.replace(/_/g, " ")}
            </span>
          </div>
          <div className="space-y-3">
            {governed.workflow_confidence.platforms.slice(0, 3).map((item) => (
              <div key={item.target} className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-950 p-4">
                <span className="text-sm font-bold text-slate-300">{item.target}</span>
                <span className={`rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-widest ${getConfidenceStyle(item.confidence)}`}>
                  {item.confidence.replace(/_/g, " ")}
                </span>
              </div>
            ))}
            {governed.workflow_confidence.platforms.length === 0 && (
              <p className="rounded-2xl border border-dashed border-slate-800 p-4 text-sm text-slate-500">No workflow confidence samples yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="mb-5 flex items-center gap-2 text-lg font-black uppercase tracking-tight text-white">
            <Award size={20} className="text-amber-400" />
            Resume Guidance
          </div>
          {topResume ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
              <p className="text-sm font-black uppercase tracking-widest text-white">{topResume.target.replace("resume:", "Variant ")}</p>
              <p className="mt-3 text-3xl font-black text-amber-400">{topResume.raw_score.toFixed(1)}%</p>
              <p className="mt-2 text-xs leading-relaxed text-slate-500">{topResume.recommended_action.replace(/_/g, " ")}</p>
              <span className={`mt-4 inline-flex rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-widest ${getConfidenceStyle(topResume.confidence)}`}>
                {topResume.sample_quality}
              </span>
            </div>
          ) : (
            <p className="rounded-2xl border border-dashed border-slate-800 p-4 text-sm text-slate-500">No resume recommendation samples yet.</p>
          )}
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="mb-5 flex items-center gap-2 text-lg font-black uppercase tracking-tight text-white">
            <RotateCcw size={20} className="text-blue-400" />
            Guided Recovery
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-2xl font-black text-white">{governed.guided_recovery.length}</p>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Open paths</p>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-2xl font-black capitalize text-white">{governed.trust_profiles.current_profile.replace(/_/g, " ")}</p>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Trust profile</p>
            </div>
          </div>
          {topAts && (
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4">
              <p className="text-sm font-black text-white">{topAts.target}</p>
              <p className="mt-1 text-xs text-slate-500">{topAts.message}</p>
            </div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data.actionable_insights.map((insight, i) => (
          <div key={`${insight.type}-${i}`} className={`p-6 rounded-2xl border ${getInsightStyle(insight.severity)}`}>
            <div className="flex items-start gap-4">
              <div className={`p-2 rounded-xl ${getInsightIconStyle(insight.severity)}`}>
                {insight.type === "STRATEGY_BOOST" ? <TrendingUp size={20} /> :
                 insight.type === "MATCH_ENGINE_WARNING" ? <AlertTriangle size={20} /> :
                 <Lightbulb size={20} />}
              </div>
              <div>
                <h4 className="font-bold text-white mb-1 uppercase text-xs tracking-widest">{insight.type}</h4>
                <p className="text-sm text-slate-300 mb-4">{insight.message}</p>
                <div className="flex items-center gap-2 text-xs font-bold text-white bg-slate-900/50 p-2 rounded-lg border border-slate-800">
                  <Zap size={12} className="text-yellow-400" />
                  NEXT ACTION: {insight.action}
                </div>
              </div>
            </div>
          </div>
        ))}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <Target className="text-blue-400" />
            <h3 className="text-xl font-bold text-white">Platform Efficiency</h3>
          </div>
          {data.source_performance.length > 0 ? (
            <div className="space-y-6">
              {data.source_performance.map((source) => (
                <div key={source.source} className="group">
                  <div className="flex justify-between items-end mb-2">
                    <div>
                      <span className="text-sm font-bold text-white uppercase tracking-wider">{source.source}</span>
                      <span className="ml-3 text-xs text-slate-500">{source.interviews} Interviews / {source.total_apps} Apps</span>
                    </div>
                    <span className="text-sm font-black text-blue-400">{source.conversion_rate}%</span>
                  </div>
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-1000"
                      style={{ width: `${Math.min(source.conversion_rate, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No source performance data yet.</p>
          )}
        </div>

        <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
          <div className="flex items-center gap-3 mb-8">
            <Award className="text-purple-400" />
            <h3 className="text-xl font-bold text-white">AI Scoring Correlation</h3>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {data.score_correlation.map((correlation) => (
              <div key={correlation.range} className="p-4 bg-slate-950 rounded-2xl border border-slate-800 flex flex-col justify-between">
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4">AI Score: {correlation.range}</span>
                <div>
                  <div className="text-2xl font-black text-white mb-1">{correlation.rate}%</div>
                  <div className="text-[10px] text-slate-500 font-bold uppercase tracking-tighter">Callback Rate</div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-8 text-xs text-slate-500 leading-relaxed italic">
            Higher scores should ideally correlate with higher callback rates. If 90-100 is lower than 75-90, consider refining your &apos;Locked Fields&apos;.
          </p>
        </div>
      </div>

      <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <BarChart3 className="text-green-400" />
          <h3 className="text-xl font-bold text-white">Resume Variant Leaderboard</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                <th className="pb-4">Variant ID</th>
                <th className="pb-4">Total Applications</th>
                <th className="pb-4">Interview Calls</th>
                <th className="pb-4">Success Rate</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {data.resume_performance.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">No resume performance data yet.</td>
                </tr>
              )}
              {data.resume_performance.map((resume) => (
                <tr key={resume.resume_id ?? "base"} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="py-4 font-bold text-white">VARIANT_{resume.resume_id ?? "BASE"}</td>
                  <td className="py-4 text-slate-400">{resume.total_apps}</td>
                  <td className="py-4 text-slate-400">{resume.interviews}</td>
                  <td className="py-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                      resume.success_rate > 15 ? "bg-green-500/10 text-green-400" : "bg-slate-800 text-slate-400"
                    }`}>
                      {resume.success_rate}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
