"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { appConfig } from "@/lib/config";
import Link from "next/link";
import { InlineLoading, SkeletonBlock, TableSkeleton } from "@/components/LoadingStates";
import { 
  FileText, 
  Plus, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  GitBranch, 
  Settings,
  Eye,
  Trash2,
  ChevronRight,
  BrainCircuit
} from "lucide-react";
import type { Resume } from "@/lib/types";

export default function ResumesPage() {
  const { data: resumes, isLoading, refetch } = useQuery<Resume[]>({
    queryKey: ["resumes"],
    queryFn: () => backendApi.profiles.me().then((profile) => profile?.resumes || [])
  });

  const completedResumes = resumes?.filter((resume) => resume.extraction_status === "COMPLETED").length ?? 0;
  const extractionQuality = resumes?.length ? Math.round((completedResumes / resumes.length) * 100) : 0;
  const normalizationPointCount = new Set(
    resumes?.flatMap((resume) => Object.keys(resume.extraction_data ?? {})) ?? []
  ).size;
  const baseResume = resumes?.find((resume) => resume.is_base);
  const uploadAccept = appConfig.allowedResumeExtensions.join(",");

  const uploadMutation = useMutation({
    mutationFn: (file: File) => {
      const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
      const maxBytes = appConfig.maxResumeSizeMb * 1024 * 1024;

      if (!appConfig.allowedResumeExtensions.includes(ext)) {
        throw new Error(`Only ${appConfig.allowedResumeExtensions.join(", ")} files are supported.`);
      }

      if (file.size > maxBytes) {
        throw new Error(`File exceeds ${appConfig.maxResumeSizeMb} MB limit.`);
      }

      return backendApi.resumes.upload(file);
    },
    onSuccess: () => refetch()
  });

  const retryMutation = useMutation({
    mutationFn: (resumeId: number) => backendApi.resumes.retry(resumeId),
    onSuccess: () => refetch(),
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "COMPLETED": return <CheckCircle2 size={16} className="text-green-500" />;
      case "PENDING": return <RefreshCw size={16} className="text-blue-500 animate-spin" />;
      case "FAILED": return <AlertCircle size={16} className="text-red-500" />;
      default: return <RefreshCw size={16} className="text-slate-500" />;
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Resume Infrastructure</h2>
          <p className="text-slate-400 mt-1">Manage variants, optimization lineage, and extraction quality.</p>
        </div>
        
        <label className={`bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-bold transition-all flex items-center gap-2 cursor-pointer shadow-lg shadow-blue-600/20 ${uploadMutation.isPending ? "pointer-events-none opacity-70" : ""}`}>
          {uploadMutation.isPending ? (
            <InlineLoading label="Uploading" />
          ) : (
            <>
              <Plus size={18} />
              Upload Resume
            </>
          )}
          <input 
            type="file" 
            accept={uploadAccept}
            className="hidden" 
            onChange={(e) => e.target.files && uploadMutation.mutate(e.target.files[0])}
          />
        </label>
      </div>

      {/* Lineage Overview */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl md:col-span-2">
          <div className="flex items-center gap-2 text-blue-400 font-bold text-xs uppercase tracking-widest mb-6">
            <GitBranch size={16} />
            Version Lineage
          </div>
          
          <div className="space-y-4">
            {isLoading ? (
              <>
                <SkeletonBlock className="h-16 rounded-xl" />
                <div className="ml-8 border-l-2 border-slate-800 pl-6 space-y-2">
                  <SkeletonBlock className="h-12 rounded-lg" />
                  <SkeletonBlock className="h-12 rounded-lg" />
                </div>
              </>
            ) : resumes?.filter(r => r.is_base).map(base => (
              <div key={base.id} className="space-y-2">
                <div className="flex items-center gap-3 p-4 bg-slate-900 border border-blue-500/30 rounded-xl">
                  <FileText className="text-blue-400" size={20} />
                  <div className="flex-1">
                    <div className="text-white font-bold text-sm">{base.name}</div>
                    <div className="text-slate-500 text-[10px] uppercase font-black tracking-tighter">BASE VERSION V{base.version}</div>
                  </div>
                  {getStatusIcon(base.extraction_status)}
                </div>
                
                {/* Variants placeholder */}
                <div className="ml-8 border-l-2 border-slate-800 pl-6 space-y-2">
                  {resumes?.filter(r => r.parent_id === base.id).map(variant => (
                    <div key={variant.id} className="flex items-center gap-3 p-3 bg-slate-900/30 border border-slate-800 rounded-lg">
                      <ChevronRight size={14} className="text-slate-600" />
                      <div className="flex-1">
                        <div className="text-slate-300 font-bold text-xs">{variant.name}</div>
                        <div className="text-slate-600 text-[10px] uppercase">OPTIMIZED FOR ROLE</div>
                      </div>
                      {getStatusIcon(variant.extraction_status)}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stats & Health */}
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
            <div className="flex items-center gap-2 text-purple-400 font-bold text-xs uppercase tracking-widest mb-4">
              <Settings size={16} />
              Extraction Quality
            </div>
            <div className="text-3xl font-black text-white">{extractionQuality}%</div>
            <p className="text-slate-500 text-xs mt-1">Completed extraction across {normalizationPointCount} normalization points.</p>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
            <div className="flex items-center gap-2 text-green-400 font-bold text-xs uppercase tracking-widest mb-4">
              <CheckCircle2 size={16} />
              Active Policy
            </div>
            <div className="text-sm text-slate-300 font-medium italic">
              {baseResume ? `Using ${baseResume.name} as the active base resume.` : "Upload a base resume to activate resume policy."}
            </div>
          </div>
        </div>
      </div>

      {/* Job List / Empty State */}
      <div className="grid gap-4">
        {isLoading ? (
          <TableSkeleton rows={4} columns={5} />
        ) : !resumes || resumes.length === 0 ? (
          <div className="bg-slate-900/50 border border-slate-800 border-dashed py-20 rounded-2xl text-center space-y-4">
            <div className="inline-flex items-center justify-center p-4 rounded-full bg-blue-600/10 border border-blue-500/20 mb-2">
              <FileText size={32} className="text-blue-500" />
            </div>
            <h3 className="text-xl font-bold text-white">No Resumes Detected</h3>
            <p className="text-slate-500 max-w-sm mx-auto">
              Upload your base resume to initialize your professional context. 
              Our AI will automatically extract your skills and sync your profile.
            </p>
            <div className="pt-4">
              <label className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all inline-flex items-center gap-2 cursor-pointer shadow-lg shadow-blue-600/20">
                {uploadMutation.isPending ? (
                  <InlineLoading label="Uploading" />
                ) : (
                  <>
                    <Plus size={18} />
                    Upload Your First PDF
                  </>
                )}
                <input 
                  type="file" 
                  accept={uploadAccept}
                  className="hidden" 
                  onChange={(e) => e.target.files && uploadMutation.mutate(e.target.files[0])}
                />
              </label>
            </div>
          </div>
        ) : (
          /* Detail Table */
          <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
            <table className="w-full text-left">
              <thead className="bg-slate-950 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest">Resume Name</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest">Type</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest">Status</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest">Created</th>
                  <th className="px-6 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {resumes?.map((resume) => (
                  <tr key={resume.id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="text-white font-bold text-sm">{resume.name}</div>
                      <div className="text-slate-500 text-xs">V{resume.version}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-tighter ${
                        resume.is_base ? "bg-blue-600/10 text-blue-400 border border-blue-600/20" : "bg-slate-800 text-slate-400"
                      }`}>
                        {resume.is_base ? "BASE" : "VARIANT"}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(resume.extraction_status)}
                        <span className="text-xs text-slate-300">{resume.extraction_status}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500">
                      {new Date(resume.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        {resume.extraction_status === "REVIEW_REQUIRED" && (
                          <Link 
                            href={`/resumes/review/${resume.id}`}
                            className="bg-blue-600/10 text-blue-400 border border-blue-600/30 px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 hover:text-white transition-all flex items-center gap-2"
                          >
                            <BrainCircuit size={12} />
                            Review Required
                          </Link>
                        )}
                        {resume.extraction_status === "FAILED" && (
                          <button
                            onClick={() => retryMutation.mutate(resume.id)}
                            disabled={retryMutation.isPending}
                            className="bg-blue-600/10 text-blue-400 border border-blue-600/30 px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 hover:text-white transition-all flex items-center gap-2 disabled:opacity-50"
                          >
                            <RefreshCw size={12} />
                            Retry
                          </button>
                        )}
                        <button className="p-2 text-slate-500 hover:text-white transition-colors"><Eye size={16} /></button>
                        <button className="p-2 text-slate-500 hover:text-red-400 transition-colors"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
