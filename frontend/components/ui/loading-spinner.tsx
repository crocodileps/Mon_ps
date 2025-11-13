import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  fullScreen?: boolean;
  className?: string;
}

export function LoadingSpinner({ fullScreen = false, className }: LoadingSpinnerProps) {
  return (
    <div
      className={cn(
        "flex items-center justify-center",
        fullScreen ? "h-screen w-screen" : "h-full w-full py-12",
        className
      )}
    >
      <Loader2 className="h-12 w-12 animate-spin text-blue-500" />
    </div>
  );
}
