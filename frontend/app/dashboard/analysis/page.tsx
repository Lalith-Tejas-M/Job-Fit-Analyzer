'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { BarChart2, FileText, CheckCircle, XCircle, ExternalLink, BookOpen, PlayCircle, Wrench, Award, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiGetJobRoles, apiAnalyzeRole, apiAnalyzeText } from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import ProgressRing from '@/components/ui/ProgressRing';

interface JobRole { role_id: string; role_name: string; industry: string; }
interface Resource { type: string; title: string; url: string; }
interface RoadmapItem {
  skill: string; hours: number; steps: string[];
  resources: Resource[]; project: string; certificate: string;
}
interface AnalysisResult {
  job_match_score: number; role_name: string;
  matched_skills: string[]; missing_skills: string[];
  recommendations: { short_term: RoadmapItem[]; medium_term: string[]; long_term: string[]; };
  scores: { semantic_score: number; skill_score: number; experience_score: number; project_score: number; education_score: number; cert_score: number; };
}

const RESOURCE_ICONS: Record<string, React.ReactNode> = {
  docs: <BookOpen size={14} />,
  course: <Award size={14} />,
  practice: <Wrench size={14} />,
  video: <PlayCircle size={14} />,
};

function RoadmapCard({ item, index }: { item: RoadmapItem; index: number }) {
  const [expanded, setExpanded] = useState(index === 0);
  const grouped: Record<string, Resource[]> = {};
  item.resources.forEach(r => { if (!grouped[r.type]) grouped[r.type] = []; grouped[r.type].push(r); });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className="bg-white/[0.04] border border-white/10 rounded-2xl overflow-hidden"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {index + 1}
          </div>
          <div>
            <div className="text-white font-semibold">{item.skill}</div>
            <div className="text-slate-500 text-xs">⏱ {item.hours}h estimated</div>
          </div>
        </div>
        {expanded ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="overflow-hidden border-t border-white/10"
          >
            <div className="p-5 space-y-5">
              {/* Steps */}
              {item.steps?.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-3">📋 Preparation Steps</p>
                  <ol className="space-y-2">
                    {item.steps.map((s, i) => (
                      <li key={i} className="text-slate-300 text-sm flex gap-2">
                        <span className="text-indigo-400 font-bold flex-shrink-0">{i + 1}.</span>
                        {s.replace(/^\d+\.\s*/, '')}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Resources */}
              {Object.entries(grouped).map(([type, resources]) => (
                <div key={type}>
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    {RESOURCE_ICONS[type]}
                    {type === 'docs' ? 'Documentation' : type === 'course' ? 'Courses' : type === 'practice' ? 'Practice' : 'Video Tutorials'}
                  </p>
                  <ul className="space-y-1.5">
                    {resources.map((r, i) => (
                      <li key={i}>
                        <a href={r.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 text-indigo-400 hover:text-indigo-300 text-sm transition-colors group">
                          <ExternalLink size={12} className="flex-shrink-0 opacity-60 group-hover:opacity-100" />
                          {r.title}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}

              {/* Project & Certificate */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                {item.project && (
                  <div className="bg-white/[0.03] border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-slate-500 mb-1">🔨 Project Idea</div>
                    <div className="text-slate-300 text-sm">{item.project}</div>
                  </div>
                )}
                {item.certificate && (
                  <div className="bg-white/[0.03] border border-white/10 rounded-xl p-3">
                    <div className="text-xs text-slate-500 mb-1">🏅 Certificate</div>
                    <div className="text-slate-300 text-sm">{item.certificate}</div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default function AnalysisPage() {
  const { user, resumeId } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<'role' | 'text'>('role');
  const [roles, setRoles] = useState<JobRole[]>([]);
  const [selectedRole, setSelectedRole] = useState('');
  const [jobText, setJobText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    apiGetJobRoles().then(setRoles).catch(console.error);
    // Load cached result
    const cached = localStorage.getItem('lastAnalysis');
    if (cached) setResult(JSON.parse(cached));
  }, []);

  const runAnalysis = async () => {
    if (!user || !resumeId) {
      setError('Please upload a resume first.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      let res, data;
      if (tab === 'role') {
        if (!selectedRole) { setError('Please select a job role.'); setLoading(false); return; }
        ({ res, data } = await apiAnalyzeRole(user.user_id, resumeId, selectedRole));
      } else {
        if (!jobText.trim()) { setError('Please paste a job description.'); setLoading(false); return; }
        ({ res, data } = await apiAnalyzeText(user.user_id, resumeId, jobText));
      }
      if (res.ok) {
        setResult(data);
        localStorage.setItem('lastAnalysis', JSON.stringify(data));
      } else {
        setError(data.error ?? 'Analysis failed.');
      }
    } catch (err: any) {
      console.error("Analysis error:", err);
      setError(`Analysis failed: ${err?.message || 'Network error'}. Ensure backend is running.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Input card */}
      <Card className="p-6">
        {/* Tabs */}
        <div className="flex gap-2 p-1 bg-white/[0.05] rounded-xl mb-6 w-fit">
          {([['role', 'Select Job Role'], ['text', 'Paste Job Description']] as const).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${tab === t ? 'bg-indigo-500 text-white shadow-lg' : 'text-slate-400 hover:text-white'}`}
            >
              {label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {tab === 'role' ? (
            <motion.div key="role" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 10 }}>
              <label className="text-sm font-medium text-slate-300 block mb-2">Target Job Role</label>
              <select
                value={selectedRole}
                onChange={e => setSelectedRole(e.target.value)}
                className="w-full bg-white/[0.06] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-all"
              >
                <option value="" className="bg-slate-900">-- Select a role --</option>
                {roles.map(r => (
                  <option key={r.role_id} value={r.role_id} className="bg-slate-900">
                    {r.role_name} ({r.industry})
                  </option>
                ))}
              </select>
            </motion.div>
          ) : (
            <motion.div key="text" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -10 }}>
              <label className="text-sm font-medium text-slate-300 block mb-2">Job Description</label>
              <textarea
                value={jobText}
                onChange={e => setJobText(e.target.value)}
                rows={8}
                placeholder="Paste any job description here…"
                className="w-full bg-white/[0.06] border border-white/10 rounded-xl px-4 py-3 text-white placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
              />
            </motion.div>
          )}
        </AnimatePresence>

        {!resumeId && (
          <div className="mt-4 flex items-center gap-2 text-amber-400 text-sm">
            <Loader2 size={14} className="animate-spin" />
            No resume uploaded yet.{' '}
            <button onClick={() => router.push('/dashboard/upload')} className="underline hover:text-amber-300">Upload one first</button>
          </div>
        )}

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-xl">
            {error}
          </motion.div>
        )}

        <Button onClick={runAnalysis} isLoading={loading} size="lg" className="w-full mt-5">
          <BarChart2 size={18} />
          {loading ? 'Analyzing… (this may take ~40s)' : 'Run Job Fit Analysis'}
        </Button>
      </Card>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div key="results" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
            {/* Score + skills */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="p-6 flex flex-col items-center">
                <ProgressRing score={Math.round(result.job_match_score)} label={result.role_name} size={150} />
              </Card>

              <Card className="p-6 md:col-span-2" delay={0.1}>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center gap-2 mb-3 text-emerald-400 text-sm font-semibold">
                      <CheckCircle size={15} />
                      Matched Skills ({result.matched_skills.length})
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {result.matched_skills.length === 0
                        ? <span className="text-slate-500 text-sm">None matched</span>
                        : result.matched_skills.map(s => <Badge key={s} variant="success">{s}</Badge>)
                      }
                    </div>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-3 text-red-400 text-sm font-semibold">
                      <XCircle size={15} />
                      Missing Skills ({result.missing_skills.length})
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {result.missing_skills.length === 0
                        ? <span className="text-slate-500 text-sm">None missing! 🎉</span>
                        : result.missing_skills.map(s => <Badge key={s} variant="danger">{s}</Badge>)
                      }
                    </div>
                  </div>
                </div>
              </Card>
            </div>

            {/* Roadmap */}
            {result.recommendations?.short_term?.length > 0 && (
              <Card className="p-6" delay={0.2}>
                <h3 className="text-white font-bold text-lg mb-1 flex items-center gap-2">
                  🚀 Career Roadmap
                </h3>
                <p className="text-slate-400 text-sm mb-5">Personalized learning path for your missing skills — with live resources fetched from the web.</p>

                <div className="space-y-3">
                  {result.recommendations.short_term.map((item, i) => (
                    <RoadmapCard key={item.skill} item={item} index={i} />
                  ))}
                </div>

                {/* Medium & Long term */}
                {result.recommendations.medium_term?.length > 0 && (
                  <div className="mt-6 pt-6 border-t border-white/10">
                    <h4 className="text-white font-semibold mb-3">📈 Medium-term Goals (3–6 months)</h4>
                    <ul className="space-y-2">
                      {result.recommendations.medium_term.map((g, i) => (
                        <li key={i} className="text-slate-400 text-sm flex gap-2"><span className="text-emerald-400">✅</span>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.recommendations.long_term?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-white/10">
                    <h4 className="text-white font-semibold mb-3">🏆 Long-term Vision (6–12 months)</h4>
                    <ul className="space-y-2">
                      {result.recommendations.long_term.map((g, i) => (
                        <li key={i} className="text-slate-400 text-sm flex gap-2"><span className="text-amber-400">🌟</span>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
