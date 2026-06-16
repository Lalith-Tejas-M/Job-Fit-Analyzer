'use client';

import { motion } from 'framer-motion';

interface ProgressRingProps {
  score: number; // 0–100
  size?: number;
  strokeWidth?: number;
  label?: string;
}

export default function ProgressRing({ score, size = 160, strokeWidth = 12, label }: ProgressRingProps) {
  const r = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 75 ? '#10B981' :
    score >= 50 ? '#6366F1' :
    score >= 30 ? '#F59E0B' :
    '#EF4444';

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          {/* Track */}
          <circle cx={size / 2} cy={size / 2} r={r} stroke="rgba(255,255,255,0.06)" strokeWidth={strokeWidth} fill="none" />
          {/* Progress */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke={color}
            strokeWidth={strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 8px ${color}80)` }}
          />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-3xl font-bold text-white"
          >
            {score}%
          </motion.span>
          {label && <span className="text-xs text-slate-400 mt-1 text-center px-2">{label}</span>}
        </div>
      </div>
    </div>
  );
}
