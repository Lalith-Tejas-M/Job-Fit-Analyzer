import Link from 'next/link';
import { Zap, ExternalLink, Code2, Rss } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-white/10 py-16 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 mb-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Zap size={16} className="text-white" />
              </div>
              <span className="text-white font-bold">Job Fit Analyzer</span>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs">
              AI-powered resume analysis, skill gap detection, and personalized career roadmaps for modern job seekers.
            </p>
            <div className="flex gap-3 mt-6">
              {[
                { icon: Code2, href: 'https://github.com/Lalith-Tejas-M/Job-Fit-Analyzer' },
                { icon: Rss, href: '#' },
                { icon: ExternalLink, href: '#' },
              ].map(({ icon: Icon, href }) => (
                <a
                  key={href}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 flex items-center justify-center rounded-xl bg-white/[0.06] border border-white/10 text-slate-400 hover:text-white hover:bg-white/[0.12] transition-all"
                >
                  <Icon size={16} />
                </a>
              ))}
            </div>
          </div>

          {/* Product */}
          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">Product</h4>
            <ul className="space-y-3">
              {['Dashboard', 'Upload Resume', 'Job Fit Analysis', 'Learning Roadmap'].map(l => (
                <li key={l}>
                  <Link href="/login" className="text-slate-500 hover:text-white text-sm transition-colors">{l}</Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Resources */}
          <div>
            <h4 className="text-white font-semibold mb-4 text-sm">Resources</h4>
            <ul className="space-y-3">
              {[
                { label: 'GitHub Repo', href: 'https://github.com/Lalith-Tejas-M/Job-Fit-Analyzer' },
                { label: 'About', href: '/dashboard/about' },
                { label: 'Sign Up', href: '/register' },
                { label: 'Login', href: '/login' },
              ].map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="text-slate-500 hover:text-white text-sm transition-colors">{label}</Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-slate-600 text-sm">
            © 2026 Job Fit Analyzer · Built with Next.js, Flask, and 🤖 AI
          </p>
          <p className="text-slate-600 text-sm">
            Made with ❤️ by Lalith Tejas
          </p>
        </div>
      </div>
    </footer>
  );
}
