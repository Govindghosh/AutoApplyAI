"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { getApiErrorMessage } from "@/lib/axios";
import {
  Send,
  ExternalLink,
  Clock,
  Play,
} from "lucide-react";
import { useState } from "react";
import WorkflowSupervisor from "@/components/WorkflowSupervisor";
import type { Job } from "@/lib/types";

const applicationStatuses = new Set(["APPLYING", "APPLYING_PENDING_APPROVAL", "APPLIED", "INTERVIEW", "REJECTED", "FAILED"]);

export default function ApplicationsPage() {
  const [selectedWorkflow, setSelectedWorkflow] = useState<number | null>(null);

  const { data: applications, isLoading } = useQuery<Job[]>({
    queryKey: ["applications"],
    queryFn: async () => {
      const jobs = await backendApi.jobs.list();
      return jobs.filter((job) => applicationStatuses.has(job.status));
    },
  });

  const inspectWorkflowMutation = useMutation({
    mutationFn: (jobId: number) => backendApi.workflows.getByJob(jobId),
    onSuccess: (workflowDetails) => {
      if (workflowDetails.workflow.id) setSelectedWorkflow(workflowDetails.workflow.id);
    },
    onError: (error) => {
      alert(getApiErrorMessage(error, "Workflow trace is not available for this application yet."));
    },
  });

  if (isLoading) return <div className="p-8 text-slate-500 animate-pulse">Loading application history...</div>;

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black tracking-tight text-white mb-2">APPLICATION HISTORY</h1>
          <p className="text-slate-400">Tracking every autonomous interaction and its real-world outcome.</p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4">
        {applications?.length === 0 && (
          <div className="bg-slate-900/50 border border-slate-800 border-dashed rounded-3xl p-10 text-center text-slate-500">
            No submitted applications yet.
          </div>
        )}

        {applications?.map((app) => (
          <div key={app.id} className="bg-slate-900/50 border border-slate-800 rounded-3xl p-6 hover:border-slate-700 transition-all group">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-6">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center border ${
                  app.status === "APPLIED" ? "bg-blue-500/10 border-blue-500/20 text-blue-400" :
                  app.status === "INTERVIEW" ? "bg-green-500/10 border-green-500/20 text-green-400" :
                  "bg-slate-800 border-slate-700 text-slate-500"
                }`}>
                  <Send size={24} />
                </div>

                <div>
                  <h3 className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">
                    {app.title}
                  </h3>
                  <div className="flex items-center gap-3 text-sm text-slate-500 mt-1">
                    <span className="font-bold text-slate-300 uppercase tracking-wider">{app.company}</span>
                    <span>&middot;</span>
                    <span className="flex items-center gap-1">
                      <Clock size={14} />
                      {new Date(app.created_at).toLocaleDateString()}
                    </span>
                    <span>&middot;</span>
                    <span className="uppercase tracking-widest text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-black">
                      {app.source}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => inspectWorkflowMutation.mutate(app.id)}
                  disabled={inspectWorkflowMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-sm font-bold transition-all border border-slate-700 disabled:opacity-50"
                >
                  <Play size={16} fill="currentColor" />
                  INSPECT WORKFLOW
                </button>

                <a
                  href={app.url}
                  target="_blank"
                  rel="noreferrer"
                  className="p-2 hover:bg-slate-800 rounded-xl text-slate-500 hover:text-white transition-all"
                >
                  <ExternalLink size={20} />
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedWorkflow && (
        <WorkflowSupervisor
          workflowId={selectedWorkflow}
          onClose={() => setSelectedWorkflow(null)}
        />
      )}
    </div>
  );
}
