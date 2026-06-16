'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  user_id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  resumeId: string | null;
  setResumeId: (id: string) => void;
  login: (user: User) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [resumeId, setResumeIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    try {
      const stored = localStorage.getItem('user');
      if (stored) setUser(JSON.parse(stored));
      const storedResumeId = localStorage.getItem('currentResumeId');
      if (storedResumeId) setResumeIdState(storedResumeId);
    } catch {}
    setIsLoading(false);
  }, []);

  const login = (userData: User) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
    router.push('/dashboard');
  };

  const logout = () => {
    setUser(null);
    setResumeIdState(null);
    localStorage.removeItem('user');
    localStorage.removeItem('currentResumeId');
    localStorage.removeItem('lastAnalysis');
    router.push('/login');
  };

  const setResumeId = (id: string) => {
    setResumeIdState(id);
    localStorage.setItem('currentResumeId', id);
  };

  return (
    <AuthContext.Provider value={{ user, resumeId, setResumeId, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
