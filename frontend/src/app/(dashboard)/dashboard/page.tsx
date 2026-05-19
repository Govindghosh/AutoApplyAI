"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  Send,
  CheckCircle,
  Zap,
  ExternalLink,
} from "lucide-react";
import { backendApi } from "@/lib/backend-api";
import type { IntelligenceStats, Job, ProfileData } from "@/lib/types";
import { ListSkeleton, MetricSkeletonGrid } from "@/components/LoadingStates";

const applicationStatuses = ["APPLIED", "INTERVIEW", "REJECTED"];

export default function DashboardPage() {
  const { data: jobs = [], isLoading: jobsLoading } = useQuery<Job[]>({
    queryKey: ["jobs"],
    queryFn: () => backendApi.jobs.list(),
  });

  const { data: profile } = useQuery<ProfileData | null>({
    queryKey: ["profile"],
    queryFn: () => backendApi.profiles.me(),
    retry: false,
  });

  const { data: intelligence } = useQuery<IntelligenceStats>({
    queryKey: ["intelligence_stats"],
    queryFn: () => backendApi.intelligence.stats(),
    retry: false,
  });

  const appliedCount = jobs.filter((job) => applicationStatuses.includes(job.status)).length;
  const interviewCount = Math.max(
    jobs.filter((job) => job.status === "INTERVIEW").length,
    intelligence?.source_performance?.reduce((sum, source) => sum + source.interviews, 0) ?? 0
  );
  const averageMatch = jobs.length
    ? Math.round(
        jobs.reduce((sum, job) => sum + (typeof job.ai_score === "number" ? job.ai_score : 0), 0) /
          jobs.length
      )
    : 0;

  const stats = [
    { name: "Jobs Scraped", value: jobs.length.toLocaleString(), icon: Briefcase, color: "text-blue-400" },
    { name: "Applications Sent", value: appliedCount.toLocaleString(), icon: Send, color: "text-purple-400" },
    { name: "Interview Calls", value: interviewCount.toLocaleString(), icon: CheckCircle, color: "text-green-400" },
    { name: "AI Match Rate", value: jobs.length ? `${averageMatch}%` : "0%", icon: Zap, color: "text-yellow-400" },
  ];

  const recentJobs = [...jobs]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);
  const interviewJobs = jobs.filter((job) => job.status === "INTERVIEW").slice(0, 5);
  const displayName = profile?.full_name?.split(" ")?.[0] || "there";

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold">Welcome back, {displayName}</h2>
        <p className="text-slate-400 mt-1">Here&apos;s what&apos;s happening with your job search today.</p>
      </div>

      {jobsLoading ? (
        <MetricSkeletonGrid />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <div key={stat.name} className="bg-slate-900 border border-slate-800 p-6 rounded-xl hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between mb-4">
                <div className={`p-2 rounded-lg bg-slate-800 ${stat.color}`}>
                  <stat.icon size={24} />
                </div>
              </div>
              <p className="text-slate-400 text-sm font-medium">{stat.name}</p>
              <h3 className="text-2xl font-bold mt-1">{stat.value}</h3>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Jobs</h3>
          {jobsLoading ? (
            <ListSkeleton compact />
          ) : recentJobs.length > 0 ? (
            <div className="space-y-3">
              {recentJobs.map((job) => (
                <a
                  key={job.id}
                  href={job.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between gap-4 rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3 hover:border-slate-700 transition-colors"
                >
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold text-white truncate">{job.title}</span>
                    <span className="block text-xs text-slate-500 truncate">{job.company}</span>
                  </span>
                  <ExternalLink size={14} className="text-slate-600 shrink-0" />
                </a>
              ))}
            </div>
          ) : (
            <div className="space-y-4 text-slate-400 text-sm">
              <p>No recent jobs found. Start the scraper to find some.</p>
            </div>
          )}
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4">Upcoming Interviews</h3>
          {jobsLoading ? (
            <ListSkeleton compact count={3} />
          ) : interviewJobs.length > 0 ? (
            <div className="space-y-3">
              {interviewJobs.map((job) => (
                <div key={job.id} className="rounded-lg border border-slate-800 bg-slate-950/60 px-4 py-3">
                  <div className="text-sm font-semibold text-white">{job.title}</div>
                  <div className="text-xs text-slate-500 mt-1">{job.company}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4 text-slate-400 text-sm">
              <p>No interviews recorded yet. Keep applying.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
