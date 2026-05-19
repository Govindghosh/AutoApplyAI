"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { getApiErrorMessage } from "@/lib/axios";
import type { Job, JobSourceSummary, JobStatus } from "@/lib/types";
import { InlineLoading, JobCardSkeleton } from "@/components/LoadingStates";
import { 
  ExternalLink, 
  Zap, 
  RefreshCw, 
  Search, 
  FileText, 
  CheckCircle2, 
  AlertCircle,
  Play,
  Check,
  ChevronDown,
  ChevronUp,
  Filter,
  X,
  BriefcaseBusiness,
  ShieldAlert,
  TrendingUp
} from "lucide-react";
import { useMemo, useState } from "react";

type JobFilter = "all" | "shortlisted" | "pending" | "applied";
type AnalysisFilter = "all" | "not_analyzed" | "analyzed" | "failed" | "actionable";
type RemoteFilter = "all" | "remote" | "hybrid" | "onsite" | "unknown";
type ScoreFilter = "all" | "60" | "70" | "80" | "90";
type SortOption = "quality" | "score" | "newest" | "source" | "company";
type AnalysisScoreField = "skills_match" | "experience_match" | "location_match" | "tech_stack_match";

const filterLabels: Record<JobFilter, string> = {
  all: "All",
  shortlisted: "Shortlisted",
  pending: "Pending",
  applied: "Applied",
};

const analysisLabels: Record<AnalysisFilter, string> = {
  all: "Any analysis",
  not_analyzed: "Needs analysis",
  analyzed: "Analyzed",
  failed: "Analysis failed",
  actionable: "Action needed",
};

const remoteLabels: Record<RemoteFilter, string> = {
  all: "Any mode",
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Unknown",
};

const scoreLabels: Record<ScoreFilter, string> = {
  all: "Any score",
  "60": "60%+",
  "70": "70%+",
  "80": "80%+",
  "90": "90%+",
};

const sortLabels: Record<SortOption, string> = {
  quality: "Best first",
  score: "Match score",
  newest: "Newest",
  source: "Portal",
  company: "Company",
};

const analyzedStatuses: JobStatus[] = [
  "ANALYZED",
  "SHORTLISTED",
  "READY_TO_APPLY",
  "APPLYING",
  "APPLYING_PENDING_APPROVAL",
  "APPLIED",
  "INTERVIEW",
  "REJECTED",
];

const scoreFields: Array<[AnalysisScoreField, string]> = [
  ["skills_match", "Skills"],
  ["experience_match", "Experience"],
  ["location_match", "Location"],
  ["tech_stack_match", "Tech stack"],
];

export default function JobsPage() {
  const [filter, setFilter] = useState<JobFilter>("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [locationFilter, setLocationFilter] = useState("all");
  const [remoteFilter, setRemoteFilter] = useState<RemoteFilter>("all");
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>("all");
  const [analysisFilter, setAnalysisFilter] = useState<AnalysisFilter>("all");
  const [sortOption, setSortOption] = useState<SortOption>("quality");
  const [textFilter, setTextFilter] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [expandedJobId, setExpandedJobId] = useState<number | null>(null);

  const { data: jobs, isLoading, refetch } = useQuery<Job[]>({
    queryKey: ["jobs"],
    queryFn: () => backendApi.jobs.list({ limit: 500 })
  });

  const { data: sourceSummary, refetch: refetchSources } = useQuery<JobSourceSummary[]>({
    queryKey: ["job-sources"],
    queryFn: () => backendApi.jobs.sources()
  });

  const scrapeMutation = useMutation({
    mutationFn: () => backendApi.jobs.scrape(),
    onSuccess: () => {
      alert("Scraper triggered!");
      refetch();
      refetchSources();
      window.setTimeout(() => {
        refetch();
        refetchSources();
      }, 2500);
    }
  });

  const analyzeMutation = useMutation({
    mutationFn: (jobId: number) => backendApi.jobs.analyze(jobId),
    onSuccess: () => {
      setActionError(null);
      refetch();
      window.setTimeout(() => refetch(), 1500);
    },
    onError: (error) => setActionError(getApiErrorMessage(error, "Unable to queue analysis."))
  });

  const analyzeScrapedMutation = useMutation({
    mutationFn: () => backendApi.jobs.analyzeScraped(),
    onSuccess: () => {
      setActionError(null);
      refetch();
      window.setTimeout(() => refetch(), 1500);
    },
    onError: (error) => setActionError(getApiErrorMessage(error, "Unable to queue scraped job analysis."))
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
      case "ANALYSIS_PENDING": return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "ANALYZING": return "bg-cyan-500/10 text-cyan-400 border-cyan-500/20";
      case "ANALYZED": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "SHORTLISTED": return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "APPLYING": return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
      case "APPLYING_PENDING_APPROVAL": return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "APPLIED": return "bg-green-500/10 text-green-400 border-green-500/20";
      case "ANALYSIS_FAILED": return "bg-red-500/10 text-red-400 border-red-500/20";
      default: return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const getAnalysisErrorMessage = (job: Job) => {
    const error = job.analysis_error?.trim();

    if (!error) {
      return "The analyzer did not return a usable response. Check the worker logs for the full error.";
    }

    if (/quota|429|rate[- ]?limit/i.test(error)) {
      return "Gemini quota is exhausted for this API key/model. Update billing or wait for quota reset, then retry.";
    }

    if (/api key|unauthenticated|permission|401|403/i.test(error)) {
      return "Gemini rejected the configured API key or permissions. Check GEMINI_API_KEY.";
    }

    return error;
  };

  const formatDetailValue = (value: unknown) => {
    if (value === null || value === undefined || value === "") return "Not available";
    if (Array.isArray(value)) return value.length ? value.join(", ") : "None";
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    return String(value);
  };

  const sourceOptions = useMemo<JobSourceSummary[]>(() => {
    if (sourceSummary?.length) return sourceSummary;

    const counts = new Map<string, number>();
    (jobs ?? []).forEach((job) => {
      const source = job.source || "Unknown";
      counts.set(source, (counts.get(source) ?? 0) + 1);
    });

    return Array.from(counts.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([source, count]) => ({ source, count, supported: true }));
  }, [jobs, sourceSummary]);

  const locationOptions = useMemo(() => {
    const counts = new Map<string, number>();
    (jobs ?? []).forEach((job) => {
      const location = job.location?.trim();
      if (!location) return;
      counts.set(location, (counts.get(location) ?? 0) + 1);
    });

    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .slice(0, 25);
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    const query = textFilter.trim().toLowerCase();
    const minScore = scoreFilter === "all" ? null : Number(scoreFilter);

    const filtered = (jobs ?? []).filter((job) => {
      if (filter === "shortlisted" && job.status !== "SHORTLISTED") return false;
      if (filter === "pending" && job.status !== "APPLYING_PENDING_APPROVAL") return false;
      if (filter === "applied" && job.status !== "APPLIED") return false;

      if (sourceFilter !== "all" && job.source !== sourceFilter) return false;
      if (locationFilter !== "all" && job.location !== locationFilter) return false;

      const remoteText = `${job.remote_type ?? ""} ${job.location ?? ""}`.toLowerCase();
      const hasRemote = remoteText.includes("remote");
      const hasHybrid = remoteText.includes("hybrid");
      if (remoteFilter === "remote" && !hasRemote) return false;
      if (remoteFilter === "hybrid" && !hasHybrid) return false;
      if (remoteFilter === "onsite" && (hasRemote || hasHybrid)) return false;
      if (remoteFilter === "unknown" && (job.remote_type || job.location)) return false;

      if (minScore !== null && (job.ai_score ?? 0) < minScore) return false;

      if (analysisFilter === "not_analyzed" && job.status !== "SCRAPED") return false;
      if (analysisFilter === "analyzed" && !analyzedStatuses.includes(job.status)) return false;
      if (analysisFilter === "failed" && job.status !== "ANALYSIS_FAILED") return false;
      if (
        analysisFilter === "actionable" &&
        !["SHORTLISTED", "APPLYING_PENDING_APPROVAL", "ANALYSIS_FAILED"].includes(job.status)
      ) {
        return false;
      }

      if (query) {
        const haystack = [
          job.title,
          job.company,
          job.location,
          job.description,
          job.salary,
          job.source,
          job.remote_type,
        ].join(" ").toLowerCase();
        if (!haystack.includes(query)) return false;
      }

      return true;
    });

    return [...filtered].sort((a, b) => {
      if (sortOption === "score") return (b.ai_score ?? 0) - (a.ai_score ?? 0);
      if (sortOption === "newest") return Date.parse(b.created_at) - Date.parse(a.created_at);
      if (sortOption === "source") return a.source.localeCompare(b.source) || a.title.localeCompare(b.title);
      if (sortOption === "company") return a.company.localeCompare(b.company) || a.title.localeCompare(b.title);
      return 0;
    });
  }, [
    analysisFilter,
    filter,
    jobs,
    locationFilter,
    remoteFilter,
    scoreFilter,
    sortOption,
    sourceFilter,
    textFilter,
  ]);

  const activeFilterCount = [
    filter !== "all",
    sourceFilter !== "all",
    locationFilter !== "all",
    remoteFilter !== "all",
    scoreFilter !== "all",
    analysisFilter !== "all",
    sortOption !== "quality",
    textFilter.trim().length > 0,
  ].filter(Boolean).length;

  const resetFilters = () => {
    setFilter("all");
    setSourceFilter("all");
    setLocationFilter("all");
    setRemoteFilter("all");
    setScoreFilter("all");
    setAnalysisFilter("all");
    setSortOption("quality");
    setTextFilter("");
  };

  const portalsWithJobs = sourceOptions.filter((source) => source.count > 0).length;

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Mission Control</h2>
          <p className="text-slate-400 mt-1">Manage resume-matched jobs and your application pipeline.</p>
        </div>
        
        <div className="flex gap-3">
          <button 
            onClick={() => scrapeMutation.mutate()}
            disabled={scrapeMutation.isPending}
            className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-lg font-medium transition-all flex items-center gap-2 border border-slate-700"
          >
            {scrapeMutation.isPending ? (
              <InlineLoading label="Scraping" />
            ) : (
              <>
                <RefreshCw size={18} />
                Find Matches
              </>
            )}
          </button>
          
          <button 
            onClick={() => analyzeScrapedMutation.mutate()}
            disabled={analyzeScrapedMutation.isPending}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20"
          >
            {analyzeScrapedMutation.isPending ? (
              <InlineLoading label="Queueing analysis" />
            ) : (
              <>
                <Zap size={18} />
                Analyze Matches
              </>
            )}
          </button>
        </div>
      </div>

      {actionError && (
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm font-bold text-amber-100">
          {actionError}
        </div>
      )}

      {/* Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: "Relevant", count: jobs?.length || 0, icon: Search },
          { label: "Shortlisted", count: jobs?.filter(j => j.status === "SHORTLISTED").length || 0, icon: Zap },
          { label: "Pending Approval", count: jobs?.filter(j => j.status === "APPLYING_PENDING_APPROVAL").length || 0, icon: AlertCircle },
          { label: "Applied", count: jobs?.filter(j => j.status === "APPLIED").length || 0, icon: CheckCircle2 },
          { label: "Portals", count: `${portalsWithJobs}/${sourceOptions.length || 0}`, icon: BriefcaseBusiness },
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
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
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

          {activeFilterCount > 0 && (
            <button
              onClick={resetFilters}
              className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-bold text-slate-300 transition-colors hover:bg-slate-800 hover:text-white"
            >
              <X size={16} />
              Reset {activeFilterCount}
            </button>
          )}
        </div>

        <div className="grid gap-3 rounded-lg border border-slate-800 bg-slate-900/60 p-3 md:grid-cols-2 xl:grid-cols-8">
          <label className="xl:col-span-2">
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Search</span>
            <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2">
              <Search size={16} className="text-slate-500" />
              <input
                value={textFilter}
                onChange={(event) => setTextFilter(event.target.value)}
                className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-100 outline-none placeholder:text-slate-600"
                placeholder="Title, company, skill"
              />
            </div>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Portal</span>
            <select
              value={sourceFilter}
              onChange={(event) => setSourceFilter(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              <option value="all">All portals</option>
              {sourceOptions.map((source) => (
                <option key={source.source} value={source.source}>
                  {source.source} ({source.count})
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Location</span>
            <select
              value={locationFilter}
              onChange={(event) => setLocationFilter(event.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              <option value="all">All locations</option>
              {locationOptions.map(([location, count]) => (
                <option key={location} value={location}>
                  {location} ({count})
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Mode</span>
            <select
              value={remoteFilter}
              onChange={(event) => setRemoteFilter(event.target.value as RemoteFilter)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              {(Object.keys(remoteLabels) as RemoteFilter[]).map((option) => (
                <option key={option} value={option}>
                  {remoteLabels[option]}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Match</span>
            <select
              value={scoreFilter}
              onChange={(event) => setScoreFilter(event.target.value as ScoreFilter)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              {(Object.keys(scoreLabels) as ScoreFilter[]).map((option) => (
                <option key={option} value={option}>
                  {scoreLabels[option]}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Analysis</span>
            <select
              value={analysisFilter}
              onChange={(event) => setAnalysisFilter(event.target.value as AnalysisFilter)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              {(Object.keys(analysisLabels) as AnalysisFilter[]).map((option) => (
                <option key={option} value={option}>
                  {analysisLabels[option]}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span className="mb-1 block text-[10px] font-black uppercase tracking-widest text-slate-500">Sort</span>
            <select
              value={sortOption}
              onChange={(event) => setSortOption(event.target.value as SortOption)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100 outline-none"
            >
              {(Object.keys(sortLabels) as SortOption[]).map((option) => (
                <option key={option} value={option}>
                  {sortLabels[option]}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="flex items-center gap-2 font-bold text-slate-400">
            <Filter size={14} />
            {filteredJobs.length} shown
          </span>
          <span className="text-slate-700">/</span>
          <span>{portalsWithJobs} of {sourceOptions.length || 0} portals have matches</span>
          {sourceOptions.slice(0, 10).map((source) => (
            <button
              key={source.source}
              onClick={() => setSourceFilter(source.source)}
              className={`rounded-md border px-2 py-1 font-bold transition-colors ${
                sourceFilter === source.source
                  ? "border-blue-500/40 bg-blue-500/10 text-blue-200"
                  : "border-slate-800 bg-slate-900 text-slate-500 hover:border-slate-700 hover:text-slate-300"
              }`}
            >
              {source.source}: {source.count}
            </button>
          ))}
        </div>
      </div>

      {/* Job List */}
      <div className="grid gap-4">
        {isLoading ? (
          <JobCardSkeleton />
        ) : filteredJobs?.length === 0 ? (
          <div className="bg-slate-900/50 border border-slate-800 border-dashed py-20 rounded-2xl text-center">
            <p className="text-slate-500">No jobs match these filters.</p>
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

                  {job.status === "ANALYSIS_FAILED" && (
                    <div className="mt-3 flex gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2 text-sm text-red-100">
                      <AlertCircle size={16} className="mt-0.5 shrink-0 text-red-300" />
                      <div className="min-w-0">
                        <p className="line-clamp-2">{getAnalysisErrorMessage(job)}</p>
                        {(job.last_analysis_model || job.analysis_attempts) && (
                          <p className="mt-1 text-xs text-red-200/70">
                            {job.last_analysis_model ? `Model: ${job.last_analysis_model}` : "Model unknown"}
                            {job.analysis_attempts ? ` / Attempts: ${job.analysis_attempts}` : ""}
                          </p>
                        )}
                      </div>
                    </div>
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
                {(job.status === "SCRAPED" || job.status === "ANALYSIS_FAILED") && (
                  <button 
                    onClick={() => analyzeMutation.mutate(job.id)}
                    disabled={analyzeMutation.isPending && analyzeMutation.variables === job.id}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    {analyzeMutation.isPending && analyzeMutation.variables === job.id
                      ? <InlineLoading label="Queueing" />
                      : (
                        <>
                          <Zap size={16} />
                          {job.status === "ANALYSIS_FAILED" ? "Retry Analysis" : "Analyze"}
                        </>
                      )}
                  </button>
                )}

                {job.status === "SHORTLISTED" && (
                  <button 
                    onClick={() => applyMutation.mutate(job.id)}
                    disabled={applyMutation.isPending}
                    className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    {applyMutation.isPending && applyMutation.variables === job.id ? (
                      <InlineLoading label="Starting" />
                    ) : (
                      <>
                        <Play size={16} fill="currentColor" />
                        Start Workflow
                      </>
                    )}
                  </button>
                )}

                {job.status === "APPLYING_PENDING_APPROVAL" && (
                  <button 
                    onClick={() => finalizeMutation.mutate(job.id)}
                    disabled={finalizeMutation.isPending}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2"
                  >
                    {finalizeMutation.isPending && finalizeMutation.variables === job.id ? (
                      <InlineLoading label="Approving" tone="green" />
                    ) : (
                      <>
                        <Check size={16} strokeWidth={3} />
                        Approve Final Submit
                      </>
                    )}
                  </button>
                )}

                <button
                  onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2 border border-slate-700"
                >
                  <FileText size={16} />
                  Details
                  {expandedJobId === job.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
              </div>

              {expandedJobId === job.id && (
                <div className="mt-6 border-t border-slate-800 pt-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    {[
                      ["Status", job.status.replace(/_/g, " ")],
                      ["Source", job.source],
                      ["Location", job.location],
                      ["Salary", job.salary],
                      ["Analysis attempts", job.analysis_attempts ?? 0],
                      ["Analysis model", job.last_analysis_model],
                    ].map(([label, value]) => (
                      <div key={label} className="min-w-0">
                        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</p>
                        <p className="mt-1 break-words text-sm font-semibold text-slate-200">{formatDetailValue(value)}</p>
                      </div>
                    ))}
                  </div>

                  {job.analysis_error && (
                    <div className="mt-5 rounded-lg border border-red-500/20 bg-red-500/10 p-4">
                      <p className="text-[10px] font-black uppercase tracking-widest text-red-300">Analysis Error</p>
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-red-100">
                        {job.analysis_error}
                      </p>
                    </div>
                  )}

                  {job.ai_analysis && (
                    <AIAnalysisPanel analysis={job.ai_analysis} />
                  )}

                  {job.description && (
                    <div className="mt-5">
                      <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Description</p>
                      <p className="mt-2 line-clamp-6 whitespace-pre-wrap text-sm leading-relaxed text-slate-400">
                        {job.description}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function AIAnalysisPanel({ analysis }: { analysis: NonNullable<Job["ai_analysis"]> }) {
  const matchScore = numberValue(analysis.match_score);
  const missingKeywords = stringList(analysis.missing_keywords);
  const improvements = stringList(analysis.resume_improvements);
  const riskLevel = stringValue(analysis.risk_level, "unknown").toLowerCase();
  const justification = stringValue(analysis.justification);

  return (
    <div className="mt-5 rounded-lg border border-blue-500/20 bg-slate-950/50 p-4">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-widest text-blue-300">AI Analysis</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-black tracking-tight text-white">
                {matchScore === null ? "--" : formatPercent(matchScore)}
              </span>
              <span className="text-xs font-black uppercase tracking-widest text-slate-500">Match</span>
            </div>
            <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-black uppercase tracking-widest ${riskTone(riskLevel)}`}>
              <ShieldAlert size={14} />
              {riskLevel} risk
            </span>
          </div>
        </div>

        {justification && (
          <div className="max-w-2xl border-l border-slate-800 pl-4 text-sm leading-relaxed text-slate-300">
            {justification}
          </div>
        )}
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {scoreFields.map(([field, label]) => (
          <ScoreMeter key={String(field)} label={label} value={numberValue(analysis[field])} />
        ))}
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <section className="min-w-0">
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Missing Keywords</p>
            <span className="text-xs font-semibold text-slate-600">{missingKeywords.length} gaps</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {missingKeywords.length ? (
              missingKeywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-full border border-amber-500/20 bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-100"
                >
                  {keyword}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">No major keyword gaps found.</span>
            )}
          </div>
        </section>

        <section className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Resume Improvements</p>
          <div className="mt-3 space-y-2">
            {improvements.length ? (
              improvements.map((item, index) => (
                <div key={`${index}-${item}`} className="flex gap-2 text-sm leading-relaxed text-slate-300">
                  <CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-400" />
                  <span>{item}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No resume changes recommended.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function ScoreMeter({ label, value }: { label: string; value: number | null }) {
  const safeValue = value === null ? 0 : Math.max(0, Math.min(100, value));

  return (
    <div className="min-w-0 rounded-lg border border-slate-800 bg-slate-900/60 p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-bold text-slate-300">{label}</span>
        <span className="inline-flex items-center gap-1 text-xs font-black text-blue-200">
          <TrendingUp size={13} />
          {value === null ? "--" : formatPercent(value)}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full ${scoreTone(safeValue)}`}
          style={{ width: `${safeValue}%` }}
        />
      </div>
    </div>
  );
}

function numberValue(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function formatPercent(value: number) {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
}

function riskTone(riskLevel: string) {
  switch (riskLevel) {
    case "low":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
    case "medium":
      return "border-amber-500/20 bg-amber-500/10 text-amber-300";
    case "high":
      return "border-red-500/20 bg-red-500/10 text-red-300";
    default:
      return "border-slate-700 bg-slate-800 text-slate-300";
  }
}

function scoreTone(score: number) {
  if (score >= 80) return "bg-emerald-400";
  if (score >= 60) return "bg-blue-400";
  if (score >= 40) return "bg-amber-400";
  return "bg-red-400";
}
