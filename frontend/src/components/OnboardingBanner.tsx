"use client";

import { useQuery } from "@tanstack/react-query";
import { backendApi } from "@/lib/backend-api";
import { ArrowRight, UserPlus } from "lucide-react";
import Link from "next/link";

export default function OnboardingBanner() {
  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile_me"],
    queryFn: () => backendApi.profiles.me()
  });

  if (isLoading || profile) return null;

  return (
    <div className="mb-8 bg-blue-600/10 border border-blue-500/30 p-4 rounded-2xl flex items-center justify-between group">
      <div className="flex items-center gap-4">
        <div className="bg-blue-600/20 p-2.5 rounded-xl">
          <UserPlus className="text-blue-400" size={24} />
        </div>
        <div>
          <h4 className="text-white font-bold text-sm">Professional Context Missing</h4>
          <p className="text-slate-400 text-xs mt-0.5">Please set up your profile to enable AI job matching and automated applications.</p>
        </div>
      </div>
      
      <Link 
        href="/profile" 
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4 py-2 rounded-lg transition-all"
      >
        Set Up Profile
        <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
      </Link>
    </div>
  );
}
