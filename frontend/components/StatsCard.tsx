import React from 'react';

interface StatsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  colorClass?: string;
}

export default function StatsCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  colorClass = 'bg-white',
}: StatsCardProps) {
  const getTrendColor = () => {
    if (trend === 'up') return 'text-success';
    if (trend === 'down') return 'text-danger';
    return 'text-gray-500';
  };

  return (
    <div className={`${colorClass} rounded-lg shadow-md p-6 border border-gray-200`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {icon && <div className="text-gray-400">{icon}</div>}
      </div>
      <div className="flex items-baseline justify-between">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        {trendValue && (
          <span className={`text-sm font-medium ${getTrendColor()}`}>
            {trend === 'up' && '↑ '}
            {trend === 'down' && '↓ '}
            {trendValue}
          </span>
        )}
      </div>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
    </div>
  );
}
