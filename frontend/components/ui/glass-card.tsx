import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  [key: string]: any;
}

export function GlassCard({ children, className = "", ...props }: GlassCardProps) {
  return (
    <div
      className={cn(
        "bg-slate-900/60 backdrop-blur-md border border-slate-700/50",
        "rounded-2xl p-4 md:p-6 transition-all duration-300",
        "hover:shadow-2xl hover:shadow-purple-500/10",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
