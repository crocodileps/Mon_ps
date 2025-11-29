import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FERRARI Intelligence - Mon_PS",
  description: "Système d'intelligence avancé pour l'analyse des paris",
};

export default function FerrariLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-red-950/20 to-slate-950">
      {children}
    </div>
  );
}
