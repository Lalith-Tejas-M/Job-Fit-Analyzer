'use client';

import Card from '@/components/ui/Card';
import { HelpCircle, Upload, BarChart2, Map, AlertTriangle } from 'lucide-react';


const steps = [
  { icon: Upload, title: 'Upload Your Resume', desc: 'Upload a PDF resume (max 5MB). Our AI extracts skills, certifications, experience, and projects automatically.' },
  { icon: BarChart2, title: 'Select or Paste a Job', desc: 'Either select from 17+ curated job roles or paste any raw job description text.' },
  { icon: Map, title: 'Get Your Analysis', desc: 'Receive an ATS match score (0-100%), a skill gap breakdown, and a personalized learning roadmap with live resources.' },
];

export default function AboutPage() {
  return (
    <div className="max-w-3xl space-y-6">
      <Card className="p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <HelpCircle size={20} className="text-white" />
          </div>
          <h2 className="text-xl font-bold text-white">About Job Fit Analyzer</h2>
        </div>
        <p className="text-slate-400 leading-relaxed">
          Job Fit Analyzer is an AI-powered career intelligence tool that helps you understand exactly how well your resume matches any job description.
          It uses semantic embeddings, LLM-based skill extraction, and real-time web research to provide actionable insights.
        </p>
      </Card>

      <Card className="p-6" delay={0.1}>
        <h3 className="text-white font-semibold mb-5">How It Works</h3>
        <div className="space-y-4">
          {steps.map(({ icon: Icon, title, desc }, i) => (
            <div key={title} className="flex gap-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/20 flex items-center justify-center flex-shrink-0">
                <Icon size={18} className="text-indigo-400" />
              </div>
              <div>
                <div className="text-white font-medium mb-1">{i + 1}. {title}</div>
                <div className="text-slate-400 text-sm">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6 border-amber-500/20" delay={0.2}>
        <div className="flex items-start gap-3">
          <AlertTriangle size={18} className="text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-amber-400 font-semibold mb-2">Limitations</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              This is a guidance tool, not a guarantee of job success. The ATS score is calculated using a hybrid model (semantic similarity + skill matching + experience + projects + education + certifications) and may not perfectly reflect a specific employer's ATS system. Use it alongside other career development strategies.
            </p>
          </div>
        </div>
      </Card>

      <Card className="p-6" delay={0.3}>
        <h3 className="text-white font-semibold mb-4">Tech Stack</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {['Next.js 14', 'React + TypeScript', 'Tailwind CSS', 'Framer Motion', 'Flask + Python', 'spaCy + LLaMA 3', 'Sentence-BERT', 'SQLite', 'yt-dlp + DuckDuckGo'].map(tech => (
            <div key={tech} className="px-3 py-2 bg-white/[0.04] border border-white/[0.08] rounded-xl text-slate-300 text-sm text-center">
              {tech}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
