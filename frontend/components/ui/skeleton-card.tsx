export function SkeletonCard() {
  return (
    <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 rounded-2xl p-6 animate-pulse">
      <div className="h-4 bg-slate-700 rounded w-3/4 mb-4"></div>
      <div className="h-8 bg-slate-700 rounded w-1/2 mb-6"></div>
      <div className="h-40 bg-slate-700 rounded"></div>
    </div>
  );
}
