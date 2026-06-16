'use client';

import { motion } from 'framer-motion';
import { Brain, BarChart2, Map, Zap, Shield, Globe } from 'lucide-react';

const features = [
  {
    icon: Brain,
    title: 'AI Skill Extraction',
    description: 'Our NLP engine + LLM extracts skills, certifications, and experience accurately from any resume format.',
    gradient: 'from-indigo-500 to-purple-600',
  },
  {
    icon: BarChart2,
    title: 'ATS Match Score',
    description: 'Get a precise 0-100% match score using semantic embeddings, skill gap analysis, and experience evaluation.',
    gradient: 'from-purple-500 to-pink-600',
  },
  {
    icon: Map,
    title: 'Personalized Roadmap',
    description: 'Receive a structured learning path per missing skill — with live-fetched YouTube tutorials and documentation.',
    gradient: 'from-cyan-500 to-blue-600',
  },
  {
    icon: Zap,
    title: 'Instant Analysis',
    description: 'Paste any job description and get analysis in seconds. No registration required for the free tier.',
    gradient: 'from-amber-500 to-orange-600',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    description: 'Your resume data is stored securely and never shared with third parties or recruiters.',
    gradient: 'from-emerald-500 to-teal-600',
  },
  {
    icon: Globe,
    title: 'Live Resources',
    description: 'Learning resources are fetched in real-time from the internet — always fresh, never outdated.',
    gradient: 'from-rose-500 to-pink-600',
  },
];

export default function FeaturesSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-sm font-medium mb-6">
            <Zap size={14} />
            Everything You Need
          </div>
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
            Powered by{' '}
            <span className="bg-gradient-to-r from-purple-400 to-cyan-400 bg-clip-text text-transparent">
              Real AI
            </span>
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Not just keyword matching — real semantic understanding of your career.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
              whileHover={{ y: -6, scale: 1.02 }}
              className="group relative bg-white/[0.05] backdrop-blur-xl border border-white/10 hover:border-white/20 rounded-2xl p-6 transition-all duration-300 overflow-hidden"
            >
              {/* Hover glow */}
              <div className={`absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br ${f.gradient} rounded-2xl blur-2xl scale-90 pointer-events-none`} style={{ opacity: 0.05 }} />

              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${f.gradient} flex items-center justify-center mb-4 shadow-lg`}>
                <f.icon size={22} className="text-white" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
