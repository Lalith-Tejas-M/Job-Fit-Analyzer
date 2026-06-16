'use client';

import { motion } from 'framer-motion';
import { Upload, BarChart2, Map } from 'lucide-react';

const steps = [
  {
    number: '01',
    icon: Upload,
    title: 'Upload Your Resume',
    description: 'Upload any PDF resume. Our AI extracts your skills, experience, education, projects, and certifications automatically.',
    gradient: 'from-indigo-500 to-purple-600',
  },
  {
    number: '02',
    icon: BarChart2,
    title: 'Analyze Job Fit',
    description: 'Select a target job role or paste any job description. Get a detailed ATS match score with semantic analysis.',
    gradient: 'from-purple-500 to-cyan-500',
  },
  {
    number: '03',
    icon: Map,
    title: 'Follow Your Roadmap',
    description: 'Get a personalized, skill-by-skill learning path with live-fetched tutorials, courses, and practice resources.',
    gradient: 'from-cyan-500 to-emerald-500',
  },
];

export default function HowItWorksSection() {
  return (
    <section className="py-24 px-6 relative">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
            How It{' '}
            <span className="bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Works
            </span>
          </h2>
          <p className="text-slate-400 text-lg">Three simple steps to career clarity.</p>
        </motion.div>

        <div className="relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-16 left-1/2 -translate-x-1/2 w-2/3 h-0.5 bg-gradient-to-r from-indigo-500/30 via-purple-500/30 to-cyan-500/30" />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
            {steps.map((step, i) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.15 }}
                className="flex flex-col items-center text-center"
              >
                <div className={`relative w-16 h-16 rounded-2xl bg-gradient-to-br ${step.gradient} flex items-center justify-center shadow-2xl mb-6`}>
                  <step.icon size={26} className="text-white" />
                  <div className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-slate-900 border-2 border-indigo-500/50 flex items-center justify-center text-indigo-400 text-xs font-bold">
                    {i + 1}
                  </div>
                </div>
                <div className="text-6xl font-black text-white/[0.04] mb-2 -mt-6 select-none">{step.number}</div>
                <h3 className="text-xl font-bold text-white mb-3">{step.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
