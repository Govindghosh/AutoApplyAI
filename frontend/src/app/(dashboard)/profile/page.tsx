"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { getApiErrorMessage } from "@/lib/axios";
import { appConfig } from "@/lib/config";
import type { ProfileData, Resume } from "@/lib/types";
import {
  User,
  Briefcase,
  FileText,
  Save,
  Upload,
  Trash2,
  Star,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  RotateCcw,
} from "lucide-react";
import { useRef, useState } from "react";

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-slate-800 text-slate-400",
  PROCESSING: "bg-amber-950 text-amber-400",
  COMPLETED: "bg-emerald-950 text-emerald-400",
  REVIEW_REQUIRED: "bg-blue-950 text-blue-400",
  FAILED: "bg-red-950 text-red-400",
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  PENDING: <Clock size={12} />,
  PROCESSING: <Loader2 size={12} className="animate-spin" />,
  COMPLETED: <CheckCircle size={12} />,
  REVIEW_REQUIRED: <AlertCircle size={12} />,
  FAILED: <AlertCircle size={12} />,
};

const defaultProfile = (): ProfileData => ({
  full_name: "",
  title: "",
  experience_years: 0,
  remote_preference: appConfig.remoteOptions[0] ?? "Remote",
  salary_expectation: 0,
  preferred_currency: appConfig.defaultCurrency,
  bio: "",
});

const normalizeProfile = (profile?: ProfileData | null): ProfileData => ({
  ...defaultProfile(),
  ...profile,
  full_name: profile?.full_name ?? "",
  title: profile?.title ?? "",
  experience_years: profile?.experience_years ?? 0,
  salary_expectation: profile?.salary_expectation ?? 0,
  preferred_currency: profile?.preferred_currency ?? appConfig.defaultCurrency,
  remote_preference: profile?.remote_preference ?? appConfig.remoteOptions[0] ?? "Remote",
  bio: profile?.bio ?? "",
});

const toProfilePayload = (data: ProfileData) => ({
  full_name: data.full_name ?? "",
  title: data.title ?? "",
  experience_years: data.experience_years ?? 0,
  remote_preference: data.remote_preference ?? appConfig.remoteOptions[0] ?? "Remote",
  salary_expectation: data.salary_expectation ?? 0,
  preferred_currency: data.preferred_currency ?? appConfig.defaultCurrency,
  bio: data.bio ?? "",
  skills: data.skills ?? [],
  tech_stack: data.tech_stack ?? {},
  preferred_roles: data.preferred_roles ?? [],
  preferred_locations: data.preferred_locations ?? [],
  work_authorization: data.work_authorization ?? null,
});

function ResumeRow({
  resume,
  onDelete,
  onRetry,
}: {
  resume: Resume;
  onDelete: (id: number) => void;
  onRetry: (id: number) => void;
}) {
  const statusStyle = STATUS_STYLES[resume.extraction_status] ?? STATUS_STYLES.PENDING;
  const statusIcon = STATUS_ICONS[resume.extraction_status] ?? STATUS_ICONS.PENDING;

  return (
    <div className="flex items-center justify-between p-4 bg-slate-950 rounded-xl border border-slate-800 group hover:border-slate-700 transition-all">
      <div className="flex items-center gap-3 min-w-0">
        <FileText size={18} className="text-slate-500 shrink-0" />
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-medium text-sm truncate">{resume.name}</span>
            {resume.is_base && (
              <span className="flex items-center gap-1 text-[10px] font-bold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full shrink-0">
                <Star size={9} />
                BASE
              </span>
            )}
          </div>
          <div className="text-xs text-slate-600 mt-0.5">
            v{resume.version} &middot; {new Date(resume.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <span className={`flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-full ${statusStyle}`}>
          {statusIcon}
          {resume.extraction_status}
        </span>
        {resume.extraction_status === "FAILED" && (
          <button
            onClick={() => onRetry(resume.id)}
            className="text-slate-500 hover:text-blue-400 transition-colors"
            title="Retry extraction"
          >
            <RotateCcw size={15} />
          </button>
        )}
        <button
          onClick={() => onDelete(resume.id)}
          className="text-slate-700 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
          title="Delete resume"
        >
          <Trash2 size={15} />
        </button>
      </div>
    </div>
  );
}

function ResumeSection({
  resumes,
  onRefetch,
}: {
  resumes: Resume[];
  onRefetch: () => void;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadAccept = appConfig.allowedResumeExtensions.join(",");
  const allowedLabel = appConfig.allowedResumeExtensions
    .map((ext) => ext.replace(".", "").toUpperCase())
    .join(", ");

  const upload = async (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const maxBytes = appConfig.maxResumeSizeMb * 1024 * 1024;

    if (!appConfig.allowedResumeExtensions.includes(ext)) {
      setError(`Only ${allowedLabel} files are supported.`);
      return;
    }

    if (file.size > maxBytes) {
      setError(`File exceeds ${appConfig.maxResumeSizeMb} MB limit.`);
      return;
    }

    setError(null);
    setUploading(true);
    try {
      await backendApi.resumes.upload(file);
      onRefetch();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Upload failed. Try again."));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) upload(file);
  };

  const handleDelete = async (id: number) => {
    try {
      await backendApi.resumes.delete(id);
      onRefetch();
    } catch {
      // non-critical
    }
  };

  const handleRetry = async (id: number) => {
    try {
      await backendApi.resumes.retry(id);
      onRefetch();
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Retry failed. Try again."));
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl space-y-5">
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2 text-orange-400 font-bold text-sm uppercase tracking-widest">
          <FileText size={16} />
          Resume Versions
        </div>
        <span className="text-xs text-slate-500">{resumes.length} file{resumes.length !== 1 ? "s" : ""}</span>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
          isDragging
            ? "border-orange-500 bg-orange-500/5"
            : "border-slate-800 hover:border-slate-600 hover:bg-slate-800/30"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={uploadAccept}
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload(file);
            e.target.value = "";
          }}
        />
        {uploading ? (
          <div className="flex flex-col items-center gap-2 text-orange-400">
            <Loader2 size={22} className="animate-spin" />
            <span className="text-sm font-medium">Uploading and queuing extraction...</span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <Upload size={22} className="text-slate-600" />
            <p className="text-sm text-slate-500">
              <span className="text-white font-medium">Drop a resume here</span> or click to browse
            </p>
            <p className="text-xs text-slate-700">{allowedLabel} &middot; Max {appConfig.maxResumeSizeMb} MB</p>
          </div>
        )}
      </div>

      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-2">
          {error}
        </div>
      )}

      {resumes.length > 0 ? (
        <div className="space-y-2">
          {resumes.map((resume) => (
            <ResumeRow key={resume.id} resume={resume} onDelete={handleDelete} onRetry={handleRetry} />
          ))}
        </div>
      ) : (
        <p className="text-center text-xs text-slate-700 pt-2">No resumes uploaded yet. The base resume drives all AI extraction.</p>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const [draftProfile, setDraftProfile] = useState<ProfileData | null>(null);

  const { data: remoteProfile, isLoading, refetch } = useQuery<ProfileData | null>({
    queryKey: ["profile"],
    queryFn: () => backendApi.profiles.me(),
    retry: false,
  });

  const profile = draftProfile ?? normalizeProfile(remoteProfile);
  const updateProfile = (updates: Partial<ProfileData>) => {
    setDraftProfile({ ...profile, ...updates });
  };

  const updateMutation = useMutation({
    mutationFn: (data: ProfileData) => {
      const payload = toProfilePayload(data);
      return remoteProfile?.id
        ? backendApi.profiles.update(payload)
        : backendApi.profiles.create(payload);
    },
    onSuccess: () => {
      setDraftProfile(null);
      refetch();
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-60 text-slate-500">
        <Loader2 size={20} className="animate-spin mr-2" />
        Loading profile...
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-4xl mx-auto pb-20">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-white tracking-tight">Professional Context</h2>
          <p className="text-slate-400 mt-1">Drives the AI Match Engine and Application Automation.</p>
        </div>
        <button
          onClick={() => updateMutation.mutate(profile)}
          disabled={updateMutation.isPending}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white px-6 py-2 rounded-xl font-bold transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20"
        >
          <Save size={18} />
          {updateMutation.isPending ? "Saving..." : "Save Context"}
        </button>
      </div>

      <div className="grid gap-6">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl space-y-6">
          <div className="flex items-center gap-2 text-blue-400 font-bold text-sm uppercase tracking-widest">
            <User size={16} />
            Basic Identity
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase">Full Name</label>
              <input
                value={profile.full_name ?? ""}
                onChange={(e) => updateProfile({ full_name: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-blue-500 outline-none transition-all"
                placeholder="John Doe"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase">Current Title</label>
              <input
                value={profile.title ?? ""}
                onChange={(e) => updateProfile({ title: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-blue-500 outline-none transition-all"
                placeholder="Senior Backend Engineer"
              />
            </div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl space-y-6">
          <div className="flex items-center gap-2 text-purple-400 font-bold text-sm uppercase tracking-widest">
            <Briefcase size={16} />
            Experience & Specs
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase">Years of Exp</label>
              <input
                type="number"
                value={profile.experience_years ?? 0}
                onChange={(e) => updateProfile({ experience_years: parseInt(e.target.value) || 0 })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-blue-500 outline-none transition-all"
              />
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase">Remote Pref</label>
              <select
                value={profile.remote_preference ?? appConfig.remoteOptions[0]}
                onChange={(e) => updateProfile({ remote_preference: e.target.value })}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-blue-500 outline-none transition-all"
              >
                {appConfig.remoteOptions.map((option) => (
                  <option key={option}>{option}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-500 uppercase">Min Salary (Annual)</label>
              <div className="relative">
                <select
                  value={profile.preferred_currency ?? appConfig.defaultCurrency}
                  onChange={(e) => updateProfile({ preferred_currency: e.target.value })}
                  className="absolute left-2 top-1/2 -translate-y-1/2 bg-transparent text-blue-500 font-bold text-xs outline-none"
                  title="Currency"
                >
                  {appConfig.currencyOptions.map((currency) => (
                    <option key={currency}>{currency}</option>
                  ))}
                </select>
                <input
                  type="number"
                  value={profile.salary_expectation ?? 0}
                  onChange={(e) => updateProfile({ salary_expectation: parseInt(e.target.value) || 0 })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 pl-20 text-white focus:border-blue-500 outline-none transition-all"
                  placeholder="150000"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-8 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 text-green-400 font-bold text-sm uppercase tracking-widest">
            <FileText size={16} />
            Professional Bio
          </div>
          <textarea
            value={profile.bio ?? ""}
            onChange={(e) => updateProfile({ bio: e.target.value })}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-4 text-white focus:border-blue-500 outline-none transition-all h-32 resize-none"
            placeholder="Summarize your professional background..."
          />
        </div>

        <ResumeSection
          resumes={remoteProfile?.resumes ?? []}
          onRefetch={refetch}
        />
      </div>
    </div>
  );
}
