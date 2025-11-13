'use client';

import { X, Briefcase, Star, AlertCircle, ThumbsDown } from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { toast } from 'react-hot-toast';

interface ClassifyBetModalProps {
  isOpen: boolean;
  onClose: () => void;
  betTitle: string;
  onClassify: (category: string) => void;
}

const CATEGORIES = [
  { 
    id: 'à_jouer', 
    label: 'À Jouer', 
    icon: Briefcase, 
    color: 'bg-blue-500/20 text-blue-400 border-blue-500/50 hover:bg-blue-500/30' 
  },
  { 
    id: 'intéressant', 
    label: 'Intéressant', 
    icon: Star, 
    color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50 hover:bg-yellow-500/30' 
  },
  { 
    id: 'trop_risqué', 
    label: 'Trop Risqué', 
    icon: AlertCircle, 
    color: 'bg-orange-500/20 text-orange-400 border-orange-500/50 hover:bg-orange-500/30' 
  },
  { 
    id: 'rejeté', 
    label: 'Rejeté', 
    icon: ThumbsDown, 
    color: 'bg-red-500/20 text-red-400 border-red-500/50 hover:bg-red-500/30' 
  },
];

export function ClassifyBetModal({ isOpen, onClose, betTitle, onClassify }: ClassifyBetModalProps) {
  if (!isOpen) return null;

  const handleClassify = (category: string) => {
    onClassify(category);
    toast.success(`Pari classé comme "${category}"`);
    onClose();
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <GlassCard 
        className="w-full max-w-2xl"
        onClick={(e: React.MouseEvent) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">📋 Classer le Pari</h2>
            <p className="text-slate-400">{betTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X className="h-6 w-6 text-slate-400" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {CATEGORIES.map((cat) => {
            const Icon = cat.icon;
            return (
              <button
                key={cat.id}
                onClick={() => handleClassify(cat.id)}
                className={`p-6 rounded-xl border-2 transition-all duration-200 hover:scale-105 ${cat.color}`}
              >
                <Icon className="h-8 w-8 mx-auto mb-3" />
                <p className="text-lg font-semibold">{cat.label}</p>
              </button>
            );
          })}
        </div>
      </GlassCard>
    </div>
  );
}
