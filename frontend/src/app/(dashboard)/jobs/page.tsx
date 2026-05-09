"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { getApiErrorMessage } from "@/lib/axios";
import type { Job, JobStatus } from "@/lib/types";
import { 
  ExternalLink, 
  Zap, 
  RefreshCw, 
  Search, 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  Play,
  Check
} from "lucide-react";
import { useState } from "react";

type JobFilter = "all" | "shortlisted" | "pending" | "applied";

const filterLabels: Record<JobFilter, string> = {
  all: "All",
  shortlisted: "Shortlisted",
  pending: "Pending",
  applied: "Applied",
};

export default function JobsPage() {
  const [filter, setFilter] = useState<JobFilter>("all");
  const [actionError, setActionError] = useState<string | null>(null);

  const { data: jobs, isLoading, refetch } = useQuery<Job[]>({
    queryKey: ["jobs"],
    queryFn: () => backendApi.jobs.list()
  });

  const scrapeMutation = useMutation({
    mutationFn: () => backendApi.jobs.scrape(),
    onSuccess: () => {
      alert("Scraper triggered!");
      refetch();
    }
  });

  const analyzeMutation = useMutation({
    mutationFn: (jobId: number) => backendApi.jobs.analyze(jobId),
    onSuccess: () => refetch()
  });

  const analyzeScrapedMutation = useMutation({
    mutationFn: () => backendApi.jobs.analyzeScraped(),
    onSuccess: () => refetch()
  });

  const applyMutation = useMutation({
    mutationFn: (jobId: number) => backendApi.jobs.apply(jobId),
    onSuccess: () => {
      setActionError(null);
      refetch();
    },
    onError: (error) => setActionError(getApiErrorMessage(error, "Unable to start workflow."))
  });

  const finalizeMutation = useMutation({
    mutationFn: (jobId: number) => backendApi.jobs.finalize(jobId),
    onSuccess: () => {
      setActionError(null);
      refetch();
    },
    onError: (error) => setActionError(getApiErrorMessage(error, "Unable to approve final submission."))
  });

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case "SCRAPED": return "bg-slate-500/10 text-slate-400 border-slate-500/20";
      case "ANALYZED": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "SHORTLISTED": return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "APPLYING": return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
      case "APPLYING_PENDING_APPROVAL": return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "APPLIED": return "bg-green-500/10 text-green-400 border-green-500/20";
      case "ANALYSIS_FAILED": return "bg-red-500/10 text-red-400 border-red-500/20";
      default: return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const filteredJobs = jobs?.filter(job => {
    if (filter === "all") return true;
    if (filter === "shortlisted") return job.status === "SHORTLISTED";
    if (filter === "pending") return job.status === "APPLYING_PENDING_APPROVAL";
    if (filter === "applied") return job.status === "APPLIED";
    return true;
  });

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Mission Control</h2>
          <p className="text-slate-400 mt-1">Manage and monitor your job automation pipeline.</p>
        </div>
        
        <div className="flex gap-3">
          <button 
            onClick={() => scrapeMutation.mutate()}
            disabled={scrapeMutation.isPending}
            className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 border border-slate-700"
          >
            <RefreshCw size={18} className={scrapeMutation.isPending ? "animate-spin" : ""} />
            {scrapeMutation.isPending ? "Scraping..." : "Run Scraper"}
          </button>
          
          <button 
            onClick={() => analyzeScrapedMutation.mutate()}
            disabled={analyzeScrapedMutation.isPending}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20"
          >
            <Zap size={18} />
            Analyze New
          </button>
        </div>
      </div>

      {actionError && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm font-bold text-amber-100">
          {actionError}
        </div>
      )}

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Scraped", count: jobs?.length || 0, icon: Search },
          { label: "Shortlisted", count: jobs?.filter(j => j.status === "SHORTLISTED").length || 0, icon: Zap },
          { label: "Pending Approval", count: jobs?.filter(j => j.status === "APPLYING_PENDING_APPROVAL").length || 0, icon: AlertCircle },
          { label: "Applied", count: jobs?.filter(j => j.status === "APPLIED").length || 0, icon: CheckCircle2 },
        ].map((stat, i) => (
          <div key={i} className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl">
            <div className="flex items-center gap-3 text-slate-400 mb-1">
              <stat.icon size={16} />
              <span className="text-xs font-semibold uppercase tracking-wider">{stat.label}</span>
            </div>
            <div className="text-2xl font-bold text-white">{stat.count}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2 p-1 bg-slate-900 border border-slate-800 rounded-lg w-fit">
        {(Object.keys(filterLabels) as JobFilter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
              filter === f ? "bg-slate-800 text-white" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {filterLabels[f]}
          </button>
        ))}
      </div>

      {/* Job List */}
      <div className="grid gap-4">
        {isLoading ? (
          <div className="flex justify-center py-20">
            <RefreshCw size={40} className="animate-spin text-blue-500" />
          </div>
        ) : filteredJobs?.length === 0 ? (
          <div className="bg-slate-900/50 border border-slate-800 border-dashed py-20 rounded-2xl text-center">
            <p className="text-slate-500">No jobs found in this category.</p>
          </div>
        ) : (
          filteredJobs?.map((job) => (
            <div key={job.id} className="bg-slate-900 border border-slate-800 p-6 rounded-2xl hover:border-slate-700 transition-all group relative overflow-hidden">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xl font-bold text-white group-hover:text-blue-400 transition-colors leading-tight">{job.title}</h3>
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${getStatusColor(job.status)}`}>
                      {job.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-slate-400 text-sm">
                    <span className="font-semibold text-slate-200">{job.company}</span>
                    <span className="text-slate-600">/</span>
                    <span>{job.location}</span>
                    <span className="text-slate-600">/</span>
                    <span className="text-slate-500 text-xs">{job.source}</span>
                  </div>

                  {job.ai_analysis?.justification && (
                    <p className="text-sm text-slate-500 line-clamp-1 mt-2 italic">
                      &ldquo;{job.ai_analysis.justification}&rdquo;
                    </p>
                  )}
                </div>

                <div className="flex flex-row md:flex-col items-end gap-3 min-w-[140px]">
                  {job.ai_score && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 text-xs font-black">
                      <Zap size={14} fill="currentColor" />
                      {Math.round(job.ai_score)}% MATCH
                    </div>
                  )}
                  
                  <div className="flex gap-2">
                    <a 
                      href={job.url} 
                      target="_blank" 
                      rel="noreferrer"
                      className="text-slate-500 hover:text-white p-2 bg-slate-800/50 rounded-lg transition-colors"
                      title="View Job Post"
                    >
                      <ExternalLink size={18} />
                    </a>
                  </div>
                </div>
              </div>
              
              <div className="mt-8 flex flex-wrap gap-3">
                {job.status === "SCRAPED" && (
                  <button 
                    onClick={() => analyzeMutation.mutate(job.id)}
                    disabled={analyzeMutation.isPending}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    <Zap size={16} />
                    Analyze
                  </button>
                )}

                {job.status === "SHORTLISTED" && (
                  <button 
                    onClick={() => applyMutation.mutate(job.id)}
                    disabled={applyMutation.isPending}
                    className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    <Play size={16} fill="currentColor" />
                    Start Workflow
                  </button>
                )}

                {job.status === "APPLYING_PENDING_APPROVAL" && (
                  <button 
                    onClick={() => finalizeMutation.mutate(job.id)}
                    disabled={finalizeMutation.isPending}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    <Check size={16} strokeWidth={3} />
                    Approve Final Submit
                  </button>
                )}

                <button className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2 border border-slate-700">
                  <FileText size={16} />
                  Details
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
