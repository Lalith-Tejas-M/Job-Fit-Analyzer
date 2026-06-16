'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings, Trash2, Eye, AlertTriangle } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiClearData } from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const [showHints, setShowHints] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [clearMsg, setClearMsg] = useState('');

  const handleClearData = async () => {
    if (!user) return;
    setClearing(true);
    try {
      const { res, data } = await apiClearData(user.user_id);
      if (res.ok) {
        localStorage.clear();
        setClearMsg(data.message ?? 'Data cleared.');
        setTimeout(() => logout(), 1500);
      } else {
        setClearMsg(data.error ?? 'Clear failed.');
      }
    } catch {
      setClearMsg('Failed. Check backend connection.');
    } finally {
      setClearing(false);
      setShowModal(false);
    }
  };

  return (
    <div className="max-w-xl space-y-6">
      <Card className="p-6">
        <h3 className="text-white font-semibold mb-5 flex items-center gap-2">
          <Settings size={16} className="text-slate-400" />
          Preferences
        </h3>

        <label className="flex items-center justify-between cursor-pointer">
          <div>
            <div className="text-white text-sm font-medium flex items-center gap-2">
              <Eye size={15} className="text-slate-400" />
              Show hint tooltips
            </div>
            <div className="text-slate-500 text-xs mt-0.5">Display helpful tips throughout the app</div>
          </div>
          <div
            onClick={() => setShowHints(!showHints)}
            className={`relative w-11 h-6 rounded-full transition-all duration-300 cursor-pointer ${showHints ? 'bg-indigo-500' : 'bg-white/10'}`}
          >
            <motion.div
              animate={{ x: showHints ? 20 : 2 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className="absolute top-1 w-4 h-4 bg-white rounded-full shadow-lg"
            />
          </div>
        </label>
      </Card>

      <Card className="p-6 border-red-500/20" delay={0.1}>
        <h3 className="text-red-400 font-semibold mb-2 flex items-center gap-2">
          <Trash2 size={16} />
          Danger Zone
        </h3>
        <p className="text-slate-500 text-sm mb-4">
          Permanently delete all your data including uploaded resumes, analyses, and your account. This action cannot be undone.
        </p>
        {clearMsg && (
          <div className="mb-4 text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 rounded-xl">
            {clearMsg}
          </div>
        )}
        <Button variant="danger" onClick={() => setShowModal(true)}>
          <Trash2 size={16} />
          Clear All Data
        </Button>
      </Card>

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Confirm Data Deletion">
        <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl mb-5">
          <AlertTriangle size={18} className="text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-red-300 text-sm">
            This will delete ALL your stored data — uploads, analyses, and your account. You will be logged out immediately.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="ghost" onClick={() => setShowModal(false)} className="flex-1">Cancel</Button>
          <Button variant="danger" isLoading={clearing} onClick={handleClearData} className="flex-1">
            Yes, Delete Everything
          </Button>
        </div>
      </Modal>
    </div>
  );
}
