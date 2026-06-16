'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

const faqs = [
  {
    q: 'Is this tool free to use?',
    a: 'Yes, Job Fit Analyzer is completely free. Create an account, upload your resume, and start analyzing job fits immediately.',
  },
  {
    q: 'What file formats are supported?',
    a: 'Currently, we support PDF resumes up to 5MB in size. More formats are coming soon.',
  },
  {
    q: 'How accurate is the skill extraction?',
    a: 'Our LLM-powered extraction achieves ~98% accuracy for technical skills, tools, certifications, and experience. It uses both spaCy NLP and a local LLaMA model.',
  },
  {
    q: 'Are the learning resources really live?',
    a: 'Yes! Unlike most tools, our roadmap resources are fetched in real-time from DuckDuckGo and YouTube via yt-dlp — not from a predefined list.',
  },
  {
    q: 'Is my resume data private?',
    a: 'Absolutely. Your resume is processed and stored locally on the server. We never share your data with recruiters, employers, or any third parties.',
  },
  {
    q: 'Can I analyze any job description?',
    a: 'Yes! Paste any raw job description text in the analysis page and we\'ll extract the required skills, compare them with your resume, and generate a personalized roadmap.',
  },
];

export default function FAQSection() {
  const [open, setOpen] = useState<number | null>(null);

  return (
    <section className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <h2 className="text-4xl md:text-5xl font-black text-white mb-4">
            Frequently Asked Questions
          </h2>
        </motion.div>

        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.06 }}
              className="bg-white/[0.05] backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden"
            >
              <button
                onClick={() => setOpen(open === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-5 text-left"
              >
                <span className="text-white font-medium">{faq.q}</span>
                <motion.div animate={{ rotate: open === i ? 180 : 0 }} transition={{ duration: 0.2 }}>
                  <ChevronDown size={18} className="text-slate-400 flex-shrink-0" />
                </motion.div>
              </button>
              <AnimatePresence>
                {open === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="px-6 pb-5 text-slate-400 text-sm leading-relaxed border-t border-white/10 pt-4">
                      {faq.a}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
