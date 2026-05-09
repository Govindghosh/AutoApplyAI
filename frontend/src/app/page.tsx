import Link from "next/link";
import { Zap, ArrowRight, Shield, Cpu, Target, CheckCircle2, PauseCircle } from "lucide-react";
import { appConfig } from "@/lib/config";

export default function LandingPage() {
  const proofItems = [
    { label: "Resume upload", state: "Completed checkpoint", icon: CheckCircle2, color: "text-green-400" },
    { label: "Custom question", state: "Paused for review", icon: PauseCircle, color: "text-amber-400" },
    { label: "Final submit", state: "Requires approval", icon: Shield, color: "text-blue-400" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 overflow-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/5 bg-slate-950/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="text-blue-500" size={28} fill="currentColor" />
            <span className="text-xl font-bold">{appConfig.appName}</span>
          </div>
          <Link 
            href="/login" 
            className="bg-white text-slate-950 px-6 py-2.5 rounded-full font-bold hover:bg-slate-200 transition-colors"
          >
            Login
          </Link>
        </div>
      </nav>

      <section className="relative pt-40 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-sm font-bold">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            Human-Supervised Beta
          </div>
          
          <h1 className="text-6xl md:text-8xl font-black tracking-tight leading-[1.1]">
            {appConfig.appName}
          </h1>
          
          <p className="text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Governed workflow orchestration for job applications: AI matching, recoverable browser automation, visible checkpoints, and approval before final submission.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link 
              href="/login" 
              className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white px-10 py-5 rounded-2xl font-black text-lg shadow-2xl shadow-blue-500/20 flex items-center justify-center gap-2 transition-all hover:scale-105 active:scale-95"
            >
              Start Supervised Beta
              <ArrowRight size={22} />
            </Link>
            <Link href="/onboarding" className="w-full sm:w-auto bg-slate-900 border border-slate-800 text-slate-200 px-10 py-5 rounded-2xl font-bold text-lg hover:bg-slate-800 transition-all">
              Review Boundaries
            </Link>
          </div>

          <div className="mx-auto mt-12 grid max-w-3xl grid-cols-1 gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-left md:grid-cols-3">
            {proofItems.map(({ label, state, icon: Icon, color }) => (
              <div key={label} className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Icon className={color} size={18} />
                  <span className="text-sm font-bold text-white">{label}</span>
                </div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{state}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-6 py-32 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="bg-slate-900/50 border border-white/5 p-8 rounded-3xl space-y-4">
          <div className="w-12 h-12 bg-blue-500/10 rounded-2xl flex items-center justify-center text-blue-500">
            <Cpu size={24} />
          </div>
          <h3 className="text-xl font-bold">AI Matching</h3>
          <p className="text-slate-400">{appConfig.aiModelLabel} reviews job descriptions against your approved profile and explains the match before workflow execution.</p>
        </div>
        
        <div className="bg-slate-900/50 border border-white/5 p-8 rounded-3xl space-y-4">
          <div className="w-12 h-12 bg-purple-500/10 rounded-2xl flex items-center justify-center text-purple-500">
            <Target size={24} />
          </div>
          <h3 className="text-xl font-bold">Checkpoint Recovery</h3>
          <p className="text-slate-400">Workflow state is durable, replayable, and inspectable when uploads, selectors, captchas, or approvals interrupt execution.</p>
        </div>

        <div className="bg-slate-900/50 border border-white/5 p-8 rounded-3xl space-y-4">
          <div className="w-12 h-12 bg-green-500/10 rounded-2xl flex items-center justify-center text-green-500">
            <Shield size={24} />
          </div>
          <h3 className="text-xl font-bold">Approval Safeguards</h3>
          <p className="text-slate-400">Daily limits, concurrency caps, and final-submit approval keep the beta inside a controlled operating envelope.</p>
        </div>
      </section>
    </div>
  );
}
