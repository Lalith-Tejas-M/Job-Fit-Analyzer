'use client';

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiHealth, apiUploadResume } from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';

const LOADING_MESSAGES = [
  '🤖 AI is reading your resume…',
  '🧠 Extracting skills with LLM…',
  '📋 Identifying projects & certifications…',
  '✅ Almost done…',
];

export default function UploadPage() {
  const { user, setResumeId } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const [msgIndex, setMsgIndex] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startLoadingMessages = useCallback(() => {
    let i = 0;
    intervalRef.current = setInterval(() => {
      i = Math.min(i + 1, LOADING_MESSAGES.length - 1);
      setMsgIndex(i);
    }, 4000);
  }, []);

  const stopLoadingMessages = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    intervalRef.current = null;
  }, []);

  const handleFile = (f: File) => {
    if (f.type !== 'application/pdf') {
      setStatus('error');
      setMessage('Only PDF files are supported.');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      setStatus('error');
      setMessage('File too large. Maximum size is 5MB.');
      return;
    }
    setFile(f);
    setStatus('idle');
    setMessage('');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const handleUpload = async () => {
    if (!file || !user) return;

    setStatus('loading');
    setMsgIndex(0);

    // Health check
    try {
      const healthy = await apiHealth();
      if (!healthy) throw new Error('not ready');
    } catch {
      setStatus('error');
      setMessage('⚠️ Backend is still loading AI models. Please wait 30–60 seconds and try again.');
      return;
    }

    startLoadingMessages();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 150000);

    try {
      const { res, data } = await apiUploadResume(file, user.user_id, controller.signal);
      clearTimeout(timeoutId);
      stopLoadingMessages();

      if (res.ok) {
        setResumeId(data.resume_id);
        setStatus('success');
        setMessage(`✅ Found ${data.skill_count} skills. Redirecting to analysis…`);
        setTimeout(() => router.push('/dashboard/analysis'), 1500);
      } else {
        setStatus('error');
        setMessage(data.error ?? 'Upload failed.');
      }
    } catch (err: any) {
      console.error("Upload error:", err);
      clearTimeout(timeoutId);
      stopLoadingMessages();
      setStatus('error');
      if (err?.name === 'AbortError') {
        setMessage('⏱️ Request timed out. The AI model is slow on CPU. Please try again.');
      } else {
        setMessage(`❌ Upload failed: ${err?.message || 'Unknown error'}. Make sure the backend server is running on port 5000.`);
      }
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <Card className="p-8">
        {/* Drop Zone */}
        <motion.div
          onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          animate={{ borderColor: isDragging ? 'rgba(99,102,241,0.6)' : file ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.1)' }}
          className="border-2 border-dashed rounded-2xl p-12 flex flex-col items-center gap-4 cursor-pointer transition-all duration-200 hover:bg-white/[0.03]"
          style={{ borderColor: 'rgba(255,255,255,0.1)' }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
          />

          <AnimatePresence mode="wait">
            {file ? (
              <motion.div key="file" initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center gap-3">
                <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <FileText size={28} className="text-emerald-400" />
                </div>
                <div className="text-white font-semibold">{file.name}</div>
                <div className="text-slate-500 text-sm">{(file.size / 1024).toFixed(1)} KB · PDF</div>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="flex flex-col items-center gap-3">
                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <Upload size={28} className="text-indigo-400" />
                </div>
                <div className="text-white font-semibold">Drop your resume here</div>
                <div className="text-slate-500 text-sm">or click to browse · PDF only · Max 5MB</div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Status message */}
        <AnimatePresence>
          {status !== 'idle' && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mt-4 overflow-hidden"
            >
              <div className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm ${
                status === 'loading' ? 'bg-indigo-500/10 border border-indigo-500/20 text-indigo-300' :
                status === 'success' ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-300' :
                'bg-red-500/10 border border-red-500/20 text-red-300'
              }`}>
                {status === 'loading' && <Loader2 size={16} className="animate-spin flex-shrink-0" />}
                {status === 'success' && <CheckCircle size={16} className="flex-shrink-0" />}
                {status === 'error' && <AlertCircle size={16} className="flex-shrink-0" />}
                <span>{status === 'loading' ? LOADING_MESSAGES[msgIndex] : message}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <Button
          onClick={handleUpload}
          isLoading={status === 'loading'}
          disabled={!file || status === 'loading'}
          size="lg"
          className="w-full mt-6"
        >
          <Upload size={18} />
          Upload & Analyze Resume
        </Button>
      </Card>

      {/* Info card */}
      <Card className="p-6" delay={0.2}>
        <h3 className="text-white font-semibold mb-3">What happens after upload?</h3>
        <ul className="space-y-2 text-slate-400 text-sm">
          {[
            'Your resume PDF is parsed and text is extracted',
            'Our LLM identifies skills, projects, experience, education, and certifications',
            'A semantic embedding is created for ATS matching',
            'You\'re redirected to the analysis page where you can pick a job role or paste a job description',
          ].map((step, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="w-5 h-5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                {i + 1}
              </span>
              {step}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
