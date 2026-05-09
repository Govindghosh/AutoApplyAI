"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { backendApi } from "@/lib/backend-api";
import type { ProfileData, Resume } from "@/lib/types";
import {
  ArrowLeft,
  Save,
  ShieldCheck,
  ShieldAlert,
  Database,
  BrainCircuit,
  Lock,
} from "lucide-react";
import { useMemo, useState } from "react";

const fieldsToReview = [
  { key: "full_name", label: "Full Name", icon: Database },
  { key: "title", label: "Professional Title", icon: Database },
  { key: "experience_years", label: "Years of Experience", icon: Database },
  { key: "skills", label: "Skills & Keywords", icon: Database },
  { key: "tech_stack", label: "Technical Stack", icon: Database },
];

export default function ExtractionReviewPage() {
  const { id } = useParams();
  const router = useRouter();
  const resumeId = Array.isArray(id) ? id[0] : id;
  const [fieldSelection, setFieldSelection] = useState<Record<string, boolean>>({});

  const { data: resume, isLoading: resumeLoading } = useQuery<Resume>({
    queryKey: ["resume", resumeId],
    queryFn: () => backendApi.resumes.get(resumeId as string),
    enabled: Boolean(resumeId),
  });

  const { data: profile, isLoading: profileLoading } = useQuery<ProfileData | null>({
    queryKey: ["profile_me"],
    queryFn: () => backendApi.profiles.me(),
  });

  const highConfidenceFields = useMemo(() => {
    if (!resume?.extraction_data) return new Set<string>();

    return new Set(
      Object.keys(resume.extraction_data).filter(
        (field) => (resume.confidence_scores?.[field] || 0) > 0.8
      )
    );
  }, [resume]);

  const approvedFields = fieldsToReview
    .map((field) => field.key)
    .filter((key) => fieldSelection[key] ?? highConfidenceFields.has(key));

  const approveMutation = useMutation({
    mutationFn: (fields: string[]) => backendApi.resumes.approve(resumeId as string, fields),
    onSuccess: () => {
      alert("Profile synchronized successfully!");
      router.push("/resumes");
    }
  });

  if (resumeLoading || profileLoading) return <div className="p-20 text-center text-slate-500">Initializing review interface...</div>;
  if (!resume) return <div className="p-20 text-center text-slate-500">Resume not found.</div>;

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.9) return <span className="bg-green-500/10 text-green-500 text-[10px] font-bold px-2 py-0.5 rounded border border-green-500/20">HIGH CONFIDENCE</span>;
    if (score >= 0.7) return <span className="bg-yellow-500/10 text-yellow-500 text-[10px] font-bold px-2 py-0.5 rounded border border-yellow-500/20">MEDIUM</span>;
    return <span className="bg-red-500/10 text-red-500 text-[10px] font-bold px-2 py-0.5 rounded border border-red-500/20">LOW - REVIEW CAREFULLY</span>;
  };

  const renderValue = (value: unknown) => {
    if (Array.isArray(value)) return value.join(", ");
    if (value && typeof value === "object") return JSON.stringify(value);
    if (value === undefined || value === null || value === "") {
      return <span className="italic opacity-50">Empty</span>;
    }
    return String(value);
  };

  const renderExtractedValue = (value: unknown) => {
    if (Array.isArray(value)) {
      return (
        <div className="flex flex-wrap gap-2">
          {value.map((item, i) => (
            <span key={`${String(item)}-${i}`} className="bg-slate-800 px-2 py-0.5 rounded text-[10px]">{String(item)}</span>
          ))}
        </div>
      );
    }

    if (value && typeof value === "object") {
      return <pre className="text-[10px] font-mono whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>;
    }

    return renderValue(value);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-20">
      <div className="flex items-center justify-between">
        <button onClick={() => router.back()} className="text-slate-400 hover:text-white flex items-center gap-2 transition-colors">
          <ArrowLeft size={18} />
          Back to Resumes
        </button>

        <button
          onClick={() => approveMutation.mutate(approvedFields)}
          disabled={approveMutation.isPending || approvedFields.length === 0}
          className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 rounded-xl font-bold transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20 disabled:opacity-50"
        >
          <Save size={18} />
          Sync {approvedFields.length} Selected Fields
        </button>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-3xl overflow-hidden shadow-2xl">
        <div className="bg-slate-950 p-8 border-b border-slate-800 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <div className="bg-blue-600/10 p-4 rounded-2xl border border-blue-500/20">
              <BrainCircuit className="text-blue-400" size={32} />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Extraction Review</h2>
              <p className="text-slate-500 text-sm mt-1">Review AI-extracted data from <span className="text-slate-300 italic">&ldquo;{resume.name}&rdquo;</span> before merging into your profile.</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Review Status</div>
            <div className="text-blue-400 font-bold uppercase text-xs mt-1">{resume.review_status}</div>
          </div>
        </div>

        <div className="p-0">
          <table className="w-full text-left">
            <thead className="bg-slate-900/50">
              <tr>
                <th className="px-8 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest w-[30%]">Data Field</th>
                <th className="px-8 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest w-[30%]">Current Profile</th>
                <th className="px-8 py-4 text-[10px] font-black uppercase text-slate-500 tracking-widest w-[40%]">AI Extracted Candidate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {fieldsToReview.map((field) => {
                const extractedValue = resume.extraction_data?.[field.key];
                const currentValue = profile?.[field.key as keyof ProfileData];
                const confidence = resume.confidence_scores?.[field.key] || 0;
                const isSelected = approvedFields.includes(field.key);
                const isLocked = profile?.locked_fields?.includes(field.key);

                return (
                  <tr key={field.key} className={`group hover:bg-slate-800/20 transition-colors ${isSelected ? "bg-blue-600/5" : ""}`}>
                    <td className="px-8 py-6">
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={isLocked}
                          onChange={() => {
                            setFieldSelection((selection) => ({
                              ...selection,
                              [field.key]: !isSelected,
                            }));
                          }}
                          className="w-5 h-5 rounded border-slate-700 bg-slate-950 text-blue-600 focus:ring-blue-500/50"
                        />
                        <div className="flex-1">
                          <div className="text-white font-bold text-sm flex items-center gap-2">
                            {field.label}
                            {isLocked && <Lock size={12} className="text-orange-400" />}
                          </div>
                          <div className="mt-2">{getConfidenceBadge(confidence)}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-6 align-top">
                      <div className="text-slate-500 text-xs font-mono break-all line-clamp-3">
                        {renderValue(currentValue)}
                      </div>
                    </td>
                    <td className="px-8 py-6 align-top">
                      <div className={cn(
                        "p-4 rounded-xl border transition-all text-sm",
                        isSelected ? "bg-blue-600/10 border-blue-500/30 text-blue-100" : "bg-slate-950 border-slate-800 text-slate-400"
                      )}>
                        {renderExtractedValue(extractedValue)}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex gap-6">
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl flex-1 flex items-start gap-4">
          <ShieldCheck className="text-green-500 mt-1" size={20} />
          <div>
            <h5 className="text-white font-bold text-sm">Automated Sync</h5>
            <p className="text-slate-500 text-xs mt-1">Fields with high confidence are automatically selected for your convenience.</p>
          </div>
        </div>
        <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl flex-1 flex items-start gap-4">
          <ShieldAlert className="text-orange-500 mt-1" size={20} />
          <div>
            <h5 className="text-white font-bold text-sm">Integrity Lock</h5>
            <p className="text-slate-500 text-xs mt-1">Fields you manually edit and lock in your profile will never be overwritten by the AI.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function cn(...inputs: Array<string | false | null | undefined>) {
  return inputs.filter(Boolean).join(" ");
}
