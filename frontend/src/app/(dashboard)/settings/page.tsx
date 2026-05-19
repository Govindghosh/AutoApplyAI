"use client";

import { useState } from "react";
import { backendApi } from "@/lib/backend-api";
import { appConfig } from "@/lib/config";
import { InlineLoading } from "@/components/LoadingStates";
import { 
  ShieldCheck, 
  Download, 
  Trash2, 
  AlertTriangle,
  Lock,
  UserCircle
} from "lucide-react";

export default function SettingsPage() {
  const [isExporting, setIsExporting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const exportData = await backendApi.auth.exportData();
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${appConfig.appName.toLowerCase()}_export_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
    } catch (err) {
      console.error("Export failed:", err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await backendApi.auth.purgeAccount();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      window.location.href = "/login";
    } catch (err) {
      console.error("Account deletion failed:", err);
      setIsDeleting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-black tracking-tight text-white mb-2">SYSTEM SETTINGS</h1>
        <p className="text-slate-400">Manage your data governance, security, and account lifecycle.</p>
      </header>

      {/* Data Governance */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <ShieldCheck className="text-blue-400" />
          <h3 className="text-xl font-bold text-white">Data Governance & Privacy</h3>
        </div>
        
        <div className="space-y-6">
          <div className="flex items-center justify-between p-6 bg-slate-950 rounded-2xl border border-slate-800">
            <div>
              <h4 className="font-bold text-white flex items-center gap-2">
                <Download size={16} className="text-slate-500" />
                Portable Data Export
              </h4>
              <p className="text-sm text-slate-500 mt-1">Download a full snapshot of your profiles, applications, and event history.</p>
            </div>
            <button 
              onClick={handleExport}
              disabled={isExporting}
              className="px-6 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50"
            >
              {isExporting ? <InlineLoading label="Exporting" /> : "Request Export"}
            </button>
          </div>

          <div className="flex items-center justify-between p-6 bg-red-500/5 rounded-2xl border border-red-500/20">
            <div>
              <h4 className="font-bold text-red-400 flex items-center gap-2">
                <Trash2 size={16} />
                Permanent Data Deletion
              </h4>
              <p className="text-sm text-slate-500 mt-1">Irretrievably purge your entire account and all associated operational history.</p>
            </div>
            <button 
              onClick={() => setShowDeleteConfirm(true)}
              className="px-6 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-xl font-bold text-sm transition-all"
            >
              Purge Account
            </button>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-3xl p-8">
        <div className="flex items-center gap-3 mb-8">
          <Lock className="text-purple-400" />
          <h3 className="text-xl font-bold text-white">Security & Access</h3>
        </div>
        <div className="text-center py-12 border-2 border-dashed border-slate-800 rounded-2xl">
          <UserCircle size={32} className="mx-auto text-slate-700 mb-4" />
          <p className="text-slate-500 text-sm">Two-Factor Authentication and API Access Management are currently being hardened.</p>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-red-500/30 rounded-3xl p-8 max-w-md w-full shadow-2xl">
            <AlertTriangle className="text-red-500 mb-6 mx-auto" size={48} />
            <h2 className="text-2xl font-black text-white text-center mb-2">EXTREME CAUTION</h2>
            <p className="text-slate-400 text-center mb-8">
              This action is <span className="text-red-400 font-bold uppercase">permanent</span>. Your resumes, job history, AI models, and all operational telemetry will be destroyed.
            </p>
            <div className="flex gap-4">
              <button 
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold"
              >
                Cancel
              </button>
              <button 
                onClick={handleDeleteAccount}
                disabled={isDeleting}
                className="flex-1 px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl font-bold disabled:opacity-60"
              >
                {isDeleting ? <InlineLoading label="Deleting" tone="amber" /> : "Confirm Deletion"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
