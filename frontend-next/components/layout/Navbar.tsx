'use client';

import { usePathname } from 'next/navigation';
import { Bell, Search } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/dashboard/upload': 'Upload Resume',
  '/dashboard/analysis': 'Job Fit Analysis',
  '/dashboard/profile': 'Profile',
  '/dashboard/settings': 'Settings',
  '/dashboard/about': 'About / Help',
};

export default function Navbar() {
  const pathname = usePathname();
  const { user } = useAuth();
  const title = PAGE_TITLES[pathname] ?? 'Dashboard';
  const initials = user?.name?.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() ?? 'U';

  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white/[0.03] backdrop-blur-xl border-b border-white/10">
      <div>
        <h1 className="text-xl font-bold text-white">{title}</h1>
        <p className="text-xs text-slate-500 mt-0.5">Welcome back, {user?.name ?? 'User'}</p>
      </div>

      <div className="flex items-center gap-3">
        {/* Search bar (UI only) */}
        <div className="hidden md:flex items-center gap-2 bg-white/[0.06] border border-white/10 rounded-xl px-3 py-2">
          <Search size={14} className="text-slate-500" />
          <input
            type="text"
            placeholder="Search..."
            className="bg-transparent text-sm text-white placeholder:text-slate-500 focus:outline-none w-36"
          />
        </div>

        {/* Notifications */}
        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl bg-white/[0.06] border border-white/10 text-slate-400 hover:text-white transition-colors">
          <Bell size={16} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-400 rounded-full" />
        </button>

        {/* Avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/30">
          {initials}
        </div>
      </div>
    </header>
  );
}
