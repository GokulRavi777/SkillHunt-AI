import React, { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { assessmentService } from '../services/api';
import { AssessmentResult } from '../types';
import {
  CheckCircle2, XCircle, AlertTriangle, ArrowRight, Clock, Award,
  HelpCircle, RefreshCw, Bot
} from 'lucide-react';

export const CompletionPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const location = useLocation();
  const navigate = useNavigate();

  const [result, setResult] = useState<AssessmentResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const initialOutcome = location.state?.outcome;

  useEffect(() => {
    const fetchResults = async () => {
      if (!sessionId) return;
      try {
        const data = await assessmentService.getResults(sessionId);
        setResult(data);
      } catch (err) {
        console.error('Error retrieving assessment results:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchResults();
  }, [sessionId]);

  const outcome = result?.terminal_outcome || initialOutcome || 'COMPLETED';

  const isSuccess = outcome === 'COMPLETED';
  const isVoluntaryTerm = outcome === 'TERMINATED_BY_CANDIDATE';
  const isGuardrailTerm = outcome === 'TERMINATED_BY_GUARDRAIL';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6">
      <div className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        {/* Status Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-4 border ${
            isSuccess
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : isVoluntaryTerm
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            {isSuccess ? (
              <CheckCircle2 className="w-10 h-10" />
            ) : isVoluntaryTerm ? (
              <AlertTriangle className="w-10 h-10" />
            ) : (
              <XCircle className="w-10 h-10" />
            )}
          </div>

          <h1 className="text-2xl font-bold text-white tracking-tight">
            {isSuccess
              ? 'Assessment Completed'
              : isVoluntaryTerm
              ? 'Interview Concluded by Candidate'
              : 'Session Terminated'}
          </h1>

          <p className="text-sm text-slate-400 mt-1 max-w-md">
            {isSuccess
              ? 'Thank you for participating! Your voice interview has been completed and your responses are safely recorded.'
              : isVoluntaryTerm
              ? 'You voluntarily ended this assessment session. Your recorded turns up to this point have been preserved.'
              : 'This assessment was terminated in accordance with interview guardrails.'}
          </p>
        </div>

        {/* Assessment Summary Metrics */}
        {result && (
          <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-5 mb-8 space-y-4">
            <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Award className="w-4 h-4 text-indigo-400" />
              Assessment Session Summary
            </h3>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/50">
                <span className="text-xs text-slate-400">Skill Domain</span>
                <p className="text-sm font-bold text-white mt-0.5">{result.selected_skill}</p>
              </div>

              <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/50">
                <span className="text-xs text-slate-400">Duration</span>
                <p className="text-sm font-bold text-white mt-0.5">
                  {Math.round(result.duration_seconds || 0)}s
                </p>
              </div>

              <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/50">
                <span className="text-xs text-slate-400">Questions Answered</span>
                <p className="text-sm font-bold text-emerald-400 mt-0.5">
                  {result.summary_metrics?.questions_answered ?? 'Recorded'}
                </p>
              </div>

              <div className="bg-slate-800/80 p-3 rounded-lg border border-slate-700/50">
                <span className="text-xs text-slate-400">Terminal Outcome</span>
                <p className="text-xs font-bold text-indigo-300 mt-1 truncate">{outcome}</p>
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex justify-between items-center pt-2">
          <button
            onClick={() => navigate('/skills')}
            className="text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Return to Domains</span>
          </button>

          <button
            onClick={() => navigate('/login')}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-6 py-2.5 rounded-xl text-sm transition"
          >
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
};
