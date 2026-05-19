import type { ReactNode } from "react";
import {
  Activity,
  BrainCircuit,
  Database,
  Loader2,
  RadioTower,
} from "lucide-react";

function cn(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

export function LoadingHalo({
  label = "Syncing",
  detail,
  className,
}: {
  label?: string;
  detail?: string;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-300">
        <Loader2 size={20} className="animate-spin" />
        <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border border-slate-950 bg-emerald-400" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-black uppercase tracking-widest text-white">{label}</p>
        {detail && <p className="mt-1 text-xs text-slate-500">{detail}</p>}
      </div>
    </div>
  );
}

export function InlineLoading({
  label,
  tone = "blue",
  className,
}: {
  label?: string;
  tone?: "blue" | "amber" | "green" | "slate";
  className?: string;
}) {
  const toneClass = {
    blue: "text-blue-300",
    amber: "text-amber-300",
    green: "text-emerald-300",
    slate: "text-slate-300",
  }[tone];

  return (
    <span className={cn("inline-flex items-center gap-2 font-bold", toneClass, className)}>
      <Loader2 size={14} className="animate-spin" />
      {label && <span>{label}</span>}
    </span>
  );
}

export function SkeletonBlock({
  className,
}: {
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-md bg-slate-800/70",
        "after:absolute after:inset-0 after:-translate-x-full after:animate-[loading-shimmer_1.4s_infinite] after:bg-gradient-to-r after:from-transparent after:via-white/10 after:to-transparent",
        className
      )}
    />
  );
}

export function MetricSkeletonGrid({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-5 flex items-center justify-between">
            <SkeletonBlock className="h-10 w-10 rounded-lg" />
            <SkeletonBlock className="h-3 w-14" />
          </div>
          <SkeletonBlock className="h-3 w-24" />
          <SkeletonBlock className="mt-3 h-7 w-20" />
        </div>
      ))}
    </div>
  );
}

export function ListSkeleton({
  count = 4,
  compact = false,
}: {
  count?: number;
  compact?: boolean;
}) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={cn(
            "rounded-xl border border-slate-800 bg-slate-950/60",
            compact ? "p-3" : "p-4"
          )}
        >
          <div className="flex items-center gap-4">
            <SkeletonBlock className="h-10 w-10 shrink-0 rounded-lg" />
            <div className="min-w-0 flex-1">
              <SkeletonBlock className="h-4 w-2/3" />
              <SkeletonBlock className="mt-2 h-3 w-1/3" />
            </div>
            <SkeletonBlock className="h-8 w-20 rounded-lg" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function JobCardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="grid gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col justify-between gap-6 md:flex-row md:items-center">
            <div className="min-w-0 flex-1 space-y-3">
              <div className="flex items-center gap-3">
                <SkeletonBlock className="h-6 w-64 max-w-full" />
                <SkeletonBlock className="h-5 w-24 rounded-full" />
              </div>
              <SkeletonBlock className="h-4 w-80 max-w-full" />
              <SkeletonBlock className="h-3 w-3/5" />
            </div>
            <div className="flex items-center gap-3 md:flex-col md:items-end">
              <SkeletonBlock className="h-8 w-28 rounded-lg" />
              <SkeletonBlock className="h-9 w-9 rounded-lg" />
            </div>
          </div>
          <div className="mt-8 flex gap-3">
            <SkeletonBlock className="h-10 w-28 rounded-xl" />
            <SkeletonBlock className="h-10 w-24 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TableSkeleton({
  rows = 5,
  columns = 5,
}: {
  rows?: number;
  columns?: number;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
      <div className="grid gap-4 border-b border-slate-800 bg-slate-950 p-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {Array.from({ length: columns }).map((_, index) => (
          <SkeletonBlock key={index} className="h-3 w-20" />
        ))}
      </div>
      <div className="divide-y divide-slate-800">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="grid gap-4 p-4" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
            {Array.from({ length: columns }).map((_, columnIndex) => (
              <SkeletonBlock key={columnIndex} className={cn("h-4", columnIndex === 0 ? "w-32" : "w-20")} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function PageLoadingState({
  title,
  subtitle,
  icon = "activity",
  children,
  className,
}: {
  title: string;
  subtitle: string;
  icon?: "activity" | "brain" | "database" | "stream";
  children?: ReactNode;
  className?: string;
}) {
  const Icon = {
    activity: Activity,
    brain: BrainCircuit,
    database: Database,
    stream: RadioTower,
  }[icon];

  return (
    <div className={cn("mx-auto max-w-7xl space-y-6", className)}>
      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-300">
              <Icon size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">{title}</h1>
              <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
            </div>
          </div>
          <LoadingHalo label="Fetching live state" detail="Keeping the interface responsive" />
        </div>
      </div>

      {children ?? (
        <>
          <MetricSkeletonGrid />
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
              <SkeletonBlock className="mb-5 h-5 w-36" />
              <ListSkeleton compact />
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
              <SkeletonBlock className="mb-5 h-5 w-40" />
              <ListSkeleton compact />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
