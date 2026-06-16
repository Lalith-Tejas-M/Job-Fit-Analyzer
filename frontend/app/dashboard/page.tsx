'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Upload, BarChart2, TrendingUp, Clock } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiGetLatestAnalysis } from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import ProgressRing from '@/components/ui/ProgressRing';

interface LatestAnalysis {
  job_match_score: number;
  role_name: string;
  missing_skills: string[];
  scores?: {
    semantic_score: number;
    skill_score: number;
    experience_score: number;
    project_score: number;
    education_score: number;
    cert_score: number;
  };
  timestamp?: string;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [analysis, setAnalysis] = useState<LatestAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      // Try cache first
      const cached = localStorage.getItem('lastAnalysis');
      if (cached) {
        setAnalysis(JSON.parse(cached));
        setLoading(false);
        return;
      }
      // Fallback to API
      if (user) {
        const data = await apiGetLatestAnalysis(user.user_id);
        if (data) setAnalysis(data);
      }
      setLoading(false);
    }
    load();
  }, [user]);

  const scoreBreakdown = analysis?.scores ? [
    { label: 'Semantic Match', value: analysis.scores.semantic_score, color: 'from-indigo-500 to-purple-500' },
    { label: 'Skills Match', value: analysis.scores.skill_score, color: 'from-cyan-500 to-blue-500' },
    { label: 'Experience', value: analysis.scores.experience_score, color: 'from-emerald-500 to-teal-500' },
    { label: 'Projects', value: analysis.scores.project_score, color: 'from-amber-500 to-orange-500' },
    { label: 'Education', value: analysis.scores.education_score, color: 'from-pink-500 to-rose-500' },
    { label: 'Certifications', value: analysis.scores.cert_score, color: 'from-violet-500 to-purple-500' },
  ] : [];

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Welcome banner */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gradient-to-r from-indigo-900/40 to-purple-900/30 backdrop-blur-xl border border-indigo-500/20 rounded-2xl p-6"
      >
        <h2 className="text-2xl font-bold text-white mb-1">
          Hello, {user?.name?.split(' ')[0]} 👋
        </h2>
        <p className="text-slate-400 text-sm">
          {analysis
            ? `Your last analysis was for "${analysis.role_name}". Keep building your skills!`
            : 'Upload your resume to get your first job fit analysis.'}
        </p>
      </motion.div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-40 bg-white/[0.04] rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : analysis ? (
        <>
          {/* Score + Role cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="p-6 flex flex-col items-center gap-4 md:col-span-1">
              <ProgressRing score={Math.round(analysis.job_match_score)} label="Overall ATS Score" />
            </Card>

            <Card className="p-6 md:col-span-2" delay={0.1}>
              <div className="flex items-center gap-2 mb-3 text-slate-400 text-xs font-medium uppercase tracking-wider">
                <TrendingUp size={14} />
                Last Analyzed Role
              </div>
              <div className="text-xl font-bold text-white mb-4">{analysis.role_name}</div>

              {analysis.missing_skills?.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">Missing Skills</p>
                  <div className="flex flex-wrap gap-2">
                    {analysis.missing_skills.slice(0, 6).map(s => (
                      <span key={s} className="px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-300 text-xs rounded-full">{s}</span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>

          {/* Score breakdown */}
          {scoreBreakdown.length > 0 && (
            <Card className="p-6" delay={0.2}>
              <div className="flex items-center gap-2 mb-5 text-slate-400 text-xs font-medium uppercase tracking-wider">
                <BarChart2 size={14} />
                Score Breakdown
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {scoreBreakdown.map((item, i) => (
                  <div key={item.label} className="flex flex-col items-center gap-2">
                    <div className="relative w-full bg-white/[0.05] rounded-xl h-2">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${item.value}%` }}
                        transition={{ duration: 1, delay: i * 0.1 }}
                        className={`h-2 rounded-xl bg-gradient-to-r ${item.color}`}
                      />
                    </div>
                    <div className="text-white font-bold text-sm">{Math.round(item.value)}%</div>
                    <div className="text-slate-500 text-xs text-center">{item.label}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card className="p-10 text-center" delay={0.1}>
          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-4">
            <BarChart2 size={28} className="text-indigo-400" />
          </div>
          <h3 className="text-white font-bold text-lg mb-2">No Analysis Yet</h3>
          <p className="text-slate-400 text-sm mb-6">Upload your resume and run a job fit analysis to see your score here.</p>
          <Button onClick={() => router.push('/dashboard/upload')}>
            <Upload size={16} />
            Upload Resume
          </Button>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card hover className="p-5 cursor-pointer" delay={0.3}>
          <button onClick={() => router.push('/dashboard/upload')} className="w-full text-left flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <Upload size={18} className="text-white" />
            </div>
            <div>
              <div className="text-white font-semibold">Upload New Resume</div>
              <div className="text-slate-500 text-sm">Replace your current resume</div>
            </div>
          </button>
        </Card>

        <Card hover className="p-5 cursor-pointer" delay={0.35}>
          <button onClick={() => router.push('/dashboard/analysis')} className="w-full text-left flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center">
              <BarChart2 size={18} className="text-white" />
            </div>
            <div>
              <div className="text-white font-semibold">Analyze Another Role</div>
              <div className="text-slate-500 text-sm">Compare your resume with a new job</div>
            </div>
          </button>
        </Card>
      </div>
    </div>
  );
}
