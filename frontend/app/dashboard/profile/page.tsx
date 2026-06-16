'use client';

import { useAuth } from '@/context/AuthContext';
import Card from '@/components/ui/Card';
import { User, Mail, Clock } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuth();
  const initials = user?.name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() ?? 'U';

  // Read last analysis from cache
  let lastRole = 'No analysis yet';
  let lastScore: number | null = null;
  try {
    const cached = localStorage.getItem('lastAnalysis');
    if (cached) {
      const data = JSON.parse(cached);
      lastRole = data.role_name;
      lastScore = Math.round(data.job_match_score);
    }
  } catch {}

  return (
    <div className="max-w-2xl space-y-6">
      {/* Avatar + name */}
      <Card className="p-8 flex items-center gap-6">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-3xl font-black shadow-2xl shadow-indigo-500/30 flex-shrink-0">
          {initials}
        </div>
        <div>
          <div className="text-2xl font-bold text-white">{user?.name}</div>
          <div className="text-slate-400 text-sm mt-1 flex items-center gap-2">
            <Mail size={14} />
            {user?.email}
          </div>
          <div className="mt-3 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            Active account
          </div>
        </div>
      </Card>

      {/* Details */}
      <Card className="p-6" delay={0.1}>
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <User size={16} className="text-slate-400" />
          Account Details
        </h3>
        <div className="space-y-4">
          {[
            { label: 'Full Name', value: user?.name ?? '—' },
            { label: 'Email Address', value: user?.email ?? '—' },
            { label: 'User ID', value: user?.user_id ?? '—' },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-3 border-b border-white/[0.06] last:border-0">
              <span className="text-slate-500 text-sm">{label}</span>
              <span className="text-white text-sm font-medium font-mono">{value}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Last analysis summary */}
      <Card className="p-6" delay={0.2}>
        <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
          <Clock size={16} className="text-slate-400" />
          Recent Analysis
        </h3>
        <div className="flex items-center justify-between p-4 bg-white/[0.04] rounded-xl border border-white/[0.06]">
          <div>
            <div className="text-white font-medium">{lastRole}</div>
            <div className="text-slate-500 text-xs mt-1">Last analyzed role</div>
          </div>
          {lastScore !== null && (
            <div className={`text-2xl font-black ${lastScore >= 75 ? 'text-emerald-400' : lastScore >= 50 ? 'text-indigo-400' : 'text-amber-400'}`}>
              {lastScore}%
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
