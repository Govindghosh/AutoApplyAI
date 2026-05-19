"use client";

import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  LifeBuoy,
  PauseCircle,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { appConfig } from "@/lib/config";
import { backendApi } from "@/lib/backend-api";
import { InlineLoading } from "@/components/LoadingStates";

export default function OnboardingPage() {
  const router = useRouter();

  const completeMutation = useMutation({
    mutationFn: () =>
      backendApi.transparency.productEvent("onboarding_completed", {
        phase: "operational_comprehension",
      }),
    onSettled: () => router.push("/jobs"),
  });

  return (
    <div className="max-w-5xl mx-auto py-12 px-6">
      <header className="mb-12">
        <h1 className="text-4xl font-black tracking-tight text-white mb-4">Operational Calibration</h1>
        <p className="text-xl text-slate-400 max-w-3xl">
          {appConfig.appName} runs governed job-application workflows. It automates repeatable steps, pauses at approval boundaries, and keeps recovery checkpoints visible.
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
        <section className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-7">
          <div className="flex items-center gap-3 mb-6">
            <Cpu className="text-blue-400" />
            <h2 className="text-lg font-bold text-white uppercase tracking-wider">Autonomous</h2>
          </div>
          <ul className="space-y-4">
            {[
              "Open known job application pages",
              "Fill approved profile fields",
              "Upload the selected resume",
              "Record durable workflow checkpoints",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-slate-300 text-sm">
                <ShieldCheck size={16} className="text-blue-500 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </section>

        <section className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-7">
          <div className="flex items-center gap-3 mb-6">
            <UserCheck className="text-amber-400" />
            <h2 className="text-lg font-bold text-white uppercase tracking-wider">Requires Approval</h2>
          </div>
          <ul className="space-y-4">
            {[
              "Final submission",
              "Ambiguous custom questions",
              "Captcha or identity challenges",
              "Unexpected platform layout changes",
            ].map((item) => (
              <li key={item} className="flex items-center gap-3 text-slate-300 text-sm">
                <ShieldAlert size={16} className="text-amber-500 shrink-0" />
                {item}
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">
        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <PauseCircle className="text-amber-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">Pause Reasons</h2>
          </div>
          <p className="text-sm leading-relaxed text-slate-400">
            A workflow pauses when the next action could change what gets submitted or when the site asks for input the system should not guess.
          </p>
        </section>

        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <LifeBuoy className="text-blue-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">Recovery</h2>
          </div>
          <p className="text-sm leading-relaxed text-slate-400">
            Completed checkpoints are preserved. Failed nodes can be replayed from the last checkpoint without duplicating completed steps.
          </p>
        </section>

        <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <AlertTriangle className="text-red-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">Known Failure Modes</h2>
          </div>
          <p className="text-sm leading-relaxed text-slate-400">
            Sites can time out, change layouts, reject uploads, or request verification. These become visible workflow states, not silent automation.
          </p>
        </section>
      </div>

      <section className="bg-slate-900/50 border border-slate-800 rounded-2xl p-8 mb-12">
        <div className="flex items-center gap-3 mb-6">
          <CheckCircle2 className="text-green-400" />
          <h2 className="text-xl font-bold text-white uppercase tracking-wider">Beta Safety Envelope</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
            <p className="text-2xl font-black text-white">{appConfig.dailyApplicationLimit}</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Daily automation limit</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
            <p className="text-2xl font-black text-white">{appConfig.workflowConcurrencyLimit}</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Concurrent workflows</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
            <p className="text-2xl font-black text-white">Approval</p>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Before final submission</p>
          </div>
        </div>
      </section>

      <div className="flex justify-start">
        <button
          onClick={() => completeMutation.mutate()}
          disabled={completeMutation.isPending}
          className="group flex items-center gap-3 bg-white text-black px-8 py-4 rounded-full font-black uppercase tracking-widest hover:bg-blue-400 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-60"
        >
          {completeMutation.isPending ? (
            <InlineLoading label="Entering dashboard" tone="slate" />
          ) : (
            <>
              Enter Dashboard
              <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
