import { GlassCard } from "./glass-card";

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

export function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (active && payload && payload.length) {
    return (
      <GlassCard className="p-4 border-blue-400/50">
        <p className="text-sm text-slate-300 font-bold">{label || payload[0].name}</p>
        {payload.map((p, i) => (
          <p key={i} className="text-sm" style={{ color: p.color || p.fill }}>
            {`${p.name}: ${typeof p.value === "number" ? p.value.toFixed(2) : p.value} ${
              p.dataKey === "pnl"
                ? "$"
                : p.dataKey === "value" && !label && !p.name.includes("ROI")
                ? "%"
                : ""
            }`}
          </p>
        ))}
      </GlassCard>
    );
  }
  return null;
}
