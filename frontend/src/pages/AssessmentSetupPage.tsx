import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { assessmentService } from '../services/api';
import {
  Mic, Volume2, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck,
  Headphones, Radio
} from 'lucide-react';

export const AssessmentSetupPage: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const sessionId = location.state?.sessionId;
  const skill = location.state?.skill || 'Python';

  const [micPermission, setMicPermission] = useState<'pending' | 'granted' | 'denied'>('pending');
  const [audioPlaybackChecked, setAudioPlaybackChecked] = useState<boolean>(false);
  const [audioTesting, setAudioTesting] = useState<boolean>(false);
  const [isStarting, setIsStarting] = useState<boolean>(false);

  useEffect(() => {
    if (!sessionId) {
      navigate('/skills');
    }
  }, [sessionId, navigate]);

  const requestMicPermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setMicPermission('granted');
      // Stop preview tracks immediately
      stream.getTracks().forEach((track) => track.stop());
    } catch (err) {
      console.error('Microphone permission denied:', err);
      setMicPermission('denied');
    }
  };

  const testAudioPlayback = () => {
    setAudioTesting(true);
    // Play a friendly synthesized confirmation tone
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, audioCtx.currentTime); // 440Hz A tone
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.8);
    setTimeout(() => {
      setAudioTesting(false);
      setAudioPlaybackChecked(true);
    }, 900);
  };

  const handleStartAssessment = async () => {
    setIsStarting(true);
    try {
      const creds = await assessmentService.startSession(sessionId);
      navigate(`/interview/${sessionId}`, { state: { credentials: creds } });
    } catch (err) {
      console.error('Error starting assessment:', err);
      setIsStarting(false);
    }
  };

  const allChecksPassed = micPermission === 'granted' && audioPlaybackChecked;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6">
      <div className="max-w-2xl w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <div className="mb-6">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold text-xs tracking-wider uppercase mb-1">
            <Radio className="w-4 h-4 animate-pulse" />
            <span>Pre-Flight Readiness Check</span>
          </div>
          <h2 className="text-2xl font-bold text-white">Assessment Setup: {skill}</h2>
          <p className="text-slate-400 text-sm mt-1">
            Please review the interview guidelines and verify your microphone and speakers before beginning.
          </p>
        </div>

        {/* Guidelines */}
        <div className="bg-slate-800/50 border border-slate-700/60 rounded-xl p-5 mb-6 space-y-2 text-sm text-slate-300">
          <h4 className="font-semibold text-white flex items-center gap-2 mb-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Interview Rules & Guidelines
          </h4>
          <ul className="list-disc pl-5 space-y-1.5 text-xs text-slate-300">
            <li>The assessment consists of three foundational technical questions with brief follow-ups.</li>
            <li>You can speak naturally at any time; Vani supports pause, resume, and clarifying examples.</li>
            <li>Ensure you are in a quiet room with minimal background noise.</li>
            <li>Headphones or earbuds are strongly recommended to avoid acoustic echo.</li>
          </ul>
        </div>

        {/* Device Checks */}
        <div className="space-y-4 mb-8">
          {/* Mic Check */}
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-lg border ${
                micPermission === 'granted'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : micPermission === 'denied'
                  ? 'bg-red-500/10 border-red-500/30 text-red-400'
                  : 'bg-slate-700/50 border-slate-600 text-slate-400'
              }`}>
                <Mic className="w-5 h-5" />
              </div>
              <div>
                <p className="font-medium text-white text-sm">Microphone Input</p>
                <p className="text-xs text-slate-400">
                  {micPermission === 'granted'
                    ? 'Microphone active and authorized'
                    : micPermission === 'denied'
                    ? 'Access denied. Please enable microphone permissions in your browser.'
                    : 'Click verify to authorize browser microphone access'}
                </p>
              </div>
            </div>

            {micPermission === 'granted' ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            ) : (
              <button
                onClick={requestMicPermission}
                className="text-xs font-semibold px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
              >
                Verify Mic
              </button>
            )}
          </div>

          {/* Speaker / Audio Check */}
          <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-lg border ${
                audioPlaybackChecked
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-slate-700/50 border-slate-600 text-slate-400'
              }`}>
                <Volume2 className="w-5 h-5" />
              </div>
              <div>
                <p className="font-medium text-white text-sm">Audio Playback</p>
                <p className="text-xs text-slate-400">
                  {audioPlaybackChecked
                    ? 'Audio output tested and verified'
                    : 'Test speaker output to ensure you can hear Vani'}
                </p>
              </div>
            </div>

            {audioPlaybackChecked ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            ) : (
              <button
                onClick={testAudioPlayback}
                disabled={audioTesting}
                className="text-xs font-semibold px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition flex items-center gap-1.5"
              >
                <Headphones className="w-3.5 h-3.5" />
                {audioTesting ? 'Testing...' : 'Test Sound'}
              </button>
            )}
          </div>
        </div>

        {/* Start Button */}
        <div className="flex justify-between items-center pt-2">
          <button
            onClick={() => navigate('/skills')}
            className="text-xs text-slate-400 hover:text-white transition"
          >
            ← Back to Domains
          </button>

          <button
            onClick={handleStartAssessment}
            disabled={!allChecksPassed || isStarting}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-medium px-8 py-3 rounded-xl flex items-center gap-2 transition duration-200 shadow-lg shadow-emerald-600/20"
          >
            {isStarting ? (
              <span className="inline-block w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <>
                <span>Start Voice Assessment</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
