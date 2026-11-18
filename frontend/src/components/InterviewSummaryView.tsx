import React, { useState } from 'react';
import type { Scorecard } from '../types';
import {
  CheckCircle,
  Award,
  ShieldCheck,
  TrendingUp,
  Download,
  RotateCcw,
  Sparkles,
  ChevronRight
} from 'lucide-react';

interface InterviewSummaryViewProps {
  scorecard: Scorecard;
  onRestart: () => void;
}

export const InterviewSummaryView: React.FC<InterviewSummaryViewProps> = ({
  scorecard,
  onRestart
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleExport = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(scorecard, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `${scorecard.candidateName}_SkillHunt_AI_Evaluation_${scorecard.persistenceId}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 3000);
  };

  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col justify-center items-center px-4 py-10">
      <div className="max-w-3xl w-full space-y-6">
        {/* Top Header Card */}
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-md shadow-2xl relative overflow-hidden">
          {/* Ambient Glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3.5">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <CheckCircle className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h2 className="text-xl font-bold text-white tracking-tight">Technical Interview Completed</h2>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold uppercase">
                    3 / 3 Questions
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Candidate: <span className="text-white font-medium">{scorecard.candidateName}</span> • {scorecard.skill} ({scorecard.proficiency}) • Duration: {scorecard.duration}
                </p>
              </div>
            </div>

            {/* Overall Score Badge */}
            <div className="text-right sm:border-l sm:border-slate-800/80 sm:pl-6">
              <div className="flex items-baseline space-x-1">
                <span className="text-3xl font-extrabold text-white">{scorecard.overallScore}</span>
                <span className="text-xs text-slate-400">/100</span>
              </div>
              <span className="inline-block mt-1 text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                {scorecard.recommendation}
              </span>
            </div>
          </div>

          {/* FastMCP Session Persistence Confirmation */}
          <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <div className="flex items-center space-x-2 text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>FastMCP Session Verification:</span>
              <span className="font-mono text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-500/30 text-[11px]">
                {scorecard.persistenceId}
              </span>
            </div>
            <span className="text-[11px] text-emerald-400 font-medium">✓ Persisted to DB</span>
          </div>
        </div>

        {/* Evaluation Metrics Breakdown */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 space-y-4">
          <div className="flex items-center space-x-2">
            <Award className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
              Core Competency Evaluation
            </h3>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {scorecard.metrics.map((metric) => (
              <div
                key={metric.label}
                className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">{metric.label}</span>
                  <span className="font-bold text-white font-mono">{metric.score}%</span>
                </div>
                <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
                    style={{ width: `${metric.score}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {metric.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Strengths & Growth Areas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Key Strengths */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-3">
            <div className="flex items-center space-x-2 text-emerald-400 text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-4 h-4" />
              <span>Key Strengths</span>
            </div>
            <ul className="space-y-2 text-xs text-slate-300">
              {scorecard.strengths.map((str, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <ChevronRight className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                  <span>{str}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Growth Areas */}
          <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 space-y-3">
            <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
              <TrendingUp className="w-4 h-4" />
              <span>Recommended Next Steps</span>
            </div>
            <ul className="space-y-2 text-xs text-slate-300">
              {scorecard.growthAreas.map((area, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <ChevronRight className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                  <span>{area}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom Actions */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
          <button
            type="button"
            onClick={onRestart}
            className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center justify-center space-x-2 border border-slate-700 transition-colors cursor-pointer"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Conduct Another Assessment</span>
          </button>

          <button
            type="button"
            onClick={handleExport}
            className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 text-white text-xs font-bold flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>{downloadSuccess ? 'Export Downloaded!' : 'Export Evaluation JSON'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
