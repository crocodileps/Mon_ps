import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Strategy V2.0 - Moteur Adaptatif | Mon_PS",
  description: "Moteur de Stratégie Adaptative V2.0 - ROI-Based, Wilson CI, Auto-Learning",
};

export default function StrategyV2Layout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {children}
    </div>
  );
}
