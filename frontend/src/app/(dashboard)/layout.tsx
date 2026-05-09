import Sidebar from "@/components/Sidebar";
import OnboardingBanner from "@/components/OnboardingBanner";
import LiveMissionControl from "@/components/LiveMissionControl";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen relative">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto bg-slate-950 pb-24">
        <OnboardingBanner />
        {children}
      </main>
      <LiveMissionControl />
    </div>
  );
}
