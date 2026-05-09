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
} from "lucide-react";
import type { IntelligenceInsight, IntelligenceStats } from "@/lib/types";

const emptyStats: IntelligenceStats = {
  actionable_insights: [],
  source_performance: [],
  score_correlation: [],
  resume_performance: [],
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

export default function IntelligenceCenter() {
  const { data = emptyStats, isLoading } = useQuery<IntelligenceStats>({
    queryKey: ["intelligence_stats"],
    queryFn: () => backendApi.intelligence.stats(),
  });

  if (isLoading) return <div className="p-8 text-slate-500 animate-pulse">Calculating operational intelligence...</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-black tracking-tight text-white mb-2">INTELLIGENCE CENTER</h1>
        <p className="text-slate-400">Operational decision support and strategy optimization.</p>
      </header>

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
