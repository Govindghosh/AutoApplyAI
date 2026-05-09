"use client";

import { useTelemetry } from "@/providers/TelemetryProvider";
import { appConfig } from "@/lib/config";
import { 
  Activity, 
  Terminal, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  BrainCircuit, 
  Search,
  Zap,
  ChevronUp,
  ChevronDown
} from "lucide-react";
import { useState } from "react";

export default function LiveMissionControl() {
  const { events, isConnected } = useTelemetry();
  const [isExpanded, setIsExpanded] = useState(false);

  const getEventIcon = (type: string) => {
    if (type.includes("FAILED")) return <AlertCircle size={14} className="text-red-500" />;
    if (type.includes("COMPLETED") || type.includes("SUCCESS")) return <CheckCircle2 size={14} className="text-green-500" />;
    if (type.includes("ANALYZING") || type.includes("PROCESSING")) return <BrainCircuit size={14} className="text-blue-400 animate-pulse" />;
    if (type.includes("SCRAPED")) return <Search size={14} className="text-purple-400" />;
    return <Zap size={14} className="text-slate-400" />;
  };

  return (
    <div className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ease-in-out ${isExpanded ? 'w-96' : 'w-64'}`}>
      <div className="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div 
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between cursor-pointer hover:bg-slate-900 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500'}`} />
            <h4 className="text-xs font-black uppercase tracking-widest text-white flex items-center gap-2">
              <Activity size={14} className="text-blue-400" />
              Mission Control
            </h4>
          </div>
          {isExpanded ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronUp size={14} className="text-slate-500" />}
        </div>

        {/* Content */}
        {isExpanded && (
          <div className="h-80 overflow-y-auto bg-slate-900 p-2 space-y-1 font-mono text-[10px]">
            {events.length === 0 ? (
              <div className="py-20 text-center text-slate-600">
                <Terminal size={24} className="mx-auto mb-2 opacity-20" />
                Waiting for system events...
              </div>
            ) : (
              events.map((event, i) => (
                <div key={i} className="p-2 rounded hover:bg-slate-800/50 flex items-start gap-3 transition-colors group">
                  <div className="mt-0.5">{getEventIcon(event.type)}</div>
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-0.5">
                      <span className="text-slate-300 font-bold group-hover:text-blue-400">{event.type}</span>
                      <span className="text-slate-600 flex items-center gap-1">
                        <Clock size={10} />
                        {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div className="text-slate-500 line-clamp-2">
                      {JSON.stringify(event.payload).replace(/[{}"]/g, '')}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Status Bar */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800 flex justify-between items-center text-[10px]">
          <span className="text-slate-500">{events.length} Events Captured</span>
          <span className="text-slate-500 italic">{appConfig.appPhase}</span>
        </div>
      </div>
    </div>
  );
}
