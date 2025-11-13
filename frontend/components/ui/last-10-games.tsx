interface Last10GamesProps {
  history: string[];
}

export function Last10Games({ history }: Last10GamesProps) {
  return (
    <div className="flex space-x-1">
      {(history || []).slice(0, 10).map((res, i) => (
        <span
          key={i}
          className={`h-5 w-2.5 rounded-sm border-b-2 ${
            res === "W"
              ? "bg-green-500 border-green-400"
              : res === "L"
              ? "bg-red-500 border-red-400"
              : "bg-yellow-500 border-yellow-400"
          }`}
          title={res}
        ></span>
      ))}
    </div>
  );
}
