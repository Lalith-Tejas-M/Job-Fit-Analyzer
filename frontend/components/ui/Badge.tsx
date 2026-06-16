interface BadgeProps {
  children: React.ReactNode;
  variant?: 'success' | 'danger' | 'info' | 'purple' | 'default';
}

const variants = {
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/20',
  danger:  'bg-red-500/15 text-red-300 border-red-500/20',
  info:    'bg-cyan-500/15 text-cyan-300 border-cyan-500/20',
  purple:  'bg-purple-500/15 text-purple-300 border-purple-500/20',
  default: 'bg-white/10 text-slate-300 border-white/10',
};

export default function Badge({ children, variant = 'default' }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${variants[variant]}`}>
      {children}
    </span>
  );
}
