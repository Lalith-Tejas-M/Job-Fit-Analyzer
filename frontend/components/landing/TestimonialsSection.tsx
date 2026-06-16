'use client';

import { motion } from 'framer-motion';
import { Star } from 'lucide-react';

const testimonials = [
  {
    name: 'Priya Sharma',
    role: 'Software Engineer',
    company: 'TCS',
    text: 'I uploaded my resume and instantly saw why I was getting rejected. The skill gap analysis was spot on — I was missing Docker and Kubernetes. Learned them in 3 weeks, got hired!',
    rating: 5,
    avatar: 'PS',
    gradient: 'from-indigo-500 to-purple-600',
  },
  {
    name: 'Rahul Mehta',
    role: 'Data Analyst',
    company: 'Infosys',
    text: 'The ATS score breakdown is incredibly detailed. Knowing my semantic score was only 36% helped me rewrite my resume and target the right roles.',
    rating: 5,
    avatar: 'RM',
    gradient: 'from-cyan-500 to-blue-600',
  },
  {
    name: 'Anjali Nair',
    role: 'ML Engineer',
    company: 'Startup',
    text: 'The roadmap with live YouTube tutorials is a game changer. Every link was fresh and relevant. I landed my dream ML role in 2 months.',
    rating: 5,
    avatar: 'AN',
    gradient: 'from-emerald-500 to-teal-600',
  },
];

export default function TestimonialsSection() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
            Loved by Job Seekers
          </h2>
          <p className="text-slate-400 text-lg">Real stories from real candidates.</p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              whileHover={{ y: -6 }}
              className="bg-white/[0.05] backdrop-blur-xl border border-white/10 rounded-2xl p-6 flex flex-col gap-4"
            >
              {/* Stars */}
              <div className="flex gap-1">
                {[...Array(t.rating)].map((_, j) => (
                  <Star key={j} size={14} className="text-amber-400 fill-amber-400" />
                ))}
              </div>
              <p className="text-slate-300 text-sm leading-relaxed flex-1">"{t.text}"</p>
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${t.gradient} flex items-center justify-center text-white text-sm font-bold flex-shrink-0`}>
                  {t.avatar}
                </div>
                <div>
                  <div className="text-white font-semibold text-sm">{t.name}</div>
                  <div className="text-slate-500 text-xs">{t.role} · {t.company}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
