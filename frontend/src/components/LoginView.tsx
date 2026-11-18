import React, { useState } from 'react';
import { DEMO_USER } from '../data/mockData';
import type { User } from '../types';
import { Bot, Key, Mail, Sparkles, ArrowRight, ShieldCheck, CheckCircle2 } from 'lucide-react';

interface LoginViewProps {
  onLoginSuccess: (user: User) => void;
}

export const LoginView: React.FC<LoginViewProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleTestCredentialFill = () => {
    setEmail(DEMO_USER.email);
    setPassword(DEMO_USER.password);
    setErrorMessage('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');

    setTimeout(() => {
      if (email.trim().toLowerCase() === DEMO_USER.email.toLowerCase()) {
        onLoginSuccess({
          name: DEMO_USER.name,
          email: DEMO_USER.email,
          role: DEMO_USER.role
        });
      } else if (email.trim().length > 3) {
        // Allow custom email for versatility
        onLoginSuccess({
          name: email.split('@')[0].replace('.', ' ').toUpperCase(),
          email: email.trim(),
          role: 'Candidate'
        });
      } else {
        setErrorMessage('Please enter a valid candidate email or use the Demo button below.');
        setIsSubmitting(false);
      }
    }, 400);
  };

  return (
    <div className="min-h-screen bg-[#080d1a] bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.18),rgba(255,255,255,0))] flex flex-col justify-center items-center px-4 py-8">
      {/* Branding Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center space-x-2.5 px-4 py-2 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-3">
          <Bot className="w-4 h-4 text-indigo-400" />
          <span>SkillHunt AI Real-Time Voice Intelligence</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
          Candidate Assessment Portal
        </h1>
        <p className="text-slate-400 text-sm mt-1.5 max-w-md mx-auto">
          Sign in to begin your AI technical interview evaluation powered by conversational guardrails and real-time voice streaming.
        </p>
      </div>

      {/* Main Glass Card */}
      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800/80 backdrop-blur-xl rounded-2xl p-7 shadow-2xl shadow-indigo-950/40">
        {/* Quick Demo Pre-Fill Action */}
        <div className="mb-6 p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Testing Mode Enabled</p>
              <p className="text-[11px] text-slate-400">Pre-fill demo candidate profile</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleTestCredentialFill}
            className="px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors flex items-center space-x-1 shadow-sm shadow-indigo-600/40 cursor-pointer"
          >
            <span>Fill Demo</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Candidate Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="candidate@example.com"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                <Key className="w-4 h-4" />
              </div>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-950/60 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
          </div>

          {errorMessage && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-medium text-sm flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isSubmitting ? (
              <span>Authenticating Candidate...</span>
            ) : (
              <>
                <span>Sign In to Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Guardrail badge */}
        <div className="mt-6 pt-5 border-t border-slate-800/80 flex items-center justify-center space-x-2 text-slate-500 text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>LiveKit Cloud & FastMCP Verified Session</span>
        </div>
      </div>

      {/* Info footer */}
      <div className="mt-8 text-center text-xs text-slate-500 flex items-center space-x-4">
        <span className="flex items-center space-x-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
          <span>Strict English Guardrail</span>
        </span>
        <span className="flex items-center space-x-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
          <span>60-Sec Hold Policy</span>
        </span>
        <span className="flex items-center space-x-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />
          <span>FastMCP Persistence</span>
        </span>
      </div>
    </div>
  );
};
