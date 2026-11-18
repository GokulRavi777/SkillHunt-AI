import React, { useState, useEffect, useRef } from 'react';
import type { InterviewConfig } from '../types';
import {
  Mic,
  Volume2,
  ShieldCheck,
  Clock,
  Globe,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  VolumeX,
  Play
} from 'lucide-react';

interface HardwareLobbyViewProps {
  config: InterviewConfig;
  onBack: () => void;
  onEnterInterview: () => void;
}

export const HardwareLobbyView: React.FC<HardwareLobbyViewProps> = ({
  config,
  onBack,
  onEnterInterview
}) => {
  const [micActive, setMicActive] = useState(false);
  const [micVolume, setMicVolume] = useState(0);
  const [speakerTested, setSpeakerTested] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [micPermissionDenied, setMicPermissionDenied] = useState(false);
  const [isPreparingSession, setIsPreparingSession] = useState(false);

  const handleStartSession = async () => {
    setIsPreparingSession(true);
    try {
      await fetch('http://127.0.0.1:8000/api/interview/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidateName: config.candidateName,
          selectedSkill: config.selectedSkill,
          proficiency: config.proficiency,
        }),
      });
    } catch (err) {
      console.warn('Backend token provision notice:', err);
    } finally {
      setIsPreparingSession(false);
      onEnterInterview();
    }
  };

  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Initialize Microphone stream
  useEffect(() => {
    let isMounted = true;

    async function initMicrophone() {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error('getUserMedia not supported');
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (!isMounted) return;

        streamRef.current = stream;
        const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        const audioCtx = new AudioCtx();
        audioContextRef.current = audioCtx;

        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        analyserRef.current = analyser;

        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);

        setMicActive(true);
        setMicPermissionDenied(false);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const updateMeter = () => {
          if (!analyserRef.current) return;
          analyserRef.current.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const average = sum / dataArray.length;
          // Scale 0-100
          const normalized = Math.min(100, Math.round((average / 128) * 100));
          setMicVolume(normalized);
          animFrameRef.current = requestAnimationFrame(updateMeter);
        };
        updateMeter();
      } catch {
        // Fallback simulated volume fluctuation if mic denied/unavailable
        if (!isMounted) return;
        setMicPermissionDenied(true);
        setMicActive(true); // Still allow proceeding in mock mode
        const interval = setInterval(() => {
          setMicVolume(Math.floor(20 + Math.random() * 35));
        }, 300);
        return () => clearInterval(interval);
      }
    }

    initMicrophone();

    return () => {
      isMounted = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  // Synthesized chime speaker test (Web Audio API)
  const handleTestSpeaker = () => {
    try {
      setIsPlayingAudio(true);
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();

      // Play 2-tone melodic chime (A4 440Hz -> E5 659Hz)
      const osc1 = ctx.createOscillator();
      const gain1 = ctx.createGain();
      osc1.type = 'sine';
      osc1.frequency.setValueAtTime(440, ctx.currentTime);
      gain1.gain.setValueAtTime(0.15, ctx.currentTime);
      gain1.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
      osc1.connect(gain1);
      gain1.connect(ctx.destination);
      osc1.start(ctx.currentTime);
      osc1.stop(ctx.currentTime + 0.4);

      const osc2 = ctx.createOscillator();
      const gain2 = ctx.createGain();
      osc2.type = 'sine';
      osc2.frequency.setValueAtTime(659.25, ctx.currentTime + 0.25);
      gain2.gain.setValueAtTime(0.18, ctx.currentTime + 0.25);
      gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.7);
      osc2.connect(gain2);
      gain2.connect(ctx.destination);
      osc2.start(ctx.currentTime + 0.25);
      osc2.stop(ctx.currentTime + 0.7);

      setTimeout(() => {
        setIsPlayingAudio(false);
        setSpeakerTested(true);
        ctx.close().catch(() => {});
      }, 750);
    } catch {
      setIsPlayingAudio(false);
      setSpeakerTested(true);
    }
  };

  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col justify-center items-center px-4 py-8">
      <div className="max-w-3xl w-full space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Change Skill / Profile</span>
          </button>
          <div className="text-right">
            <span className="text-xs text-slate-400">Target Assessment:</span>
            <span className="ml-2 px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-semibold">
              {config.selectedSkill} ({config.proficiency})
            </span>
          </div>
        </div>

        <div className="text-center space-y-2">
          <h2 className="text-3xl font-extrabold text-white tracking-tight">Hardware & Readiness Check</h2>
          <p className="text-slate-400 text-sm max-w-lg mx-auto">
            Please verify your audio inputs and review the conversational guardrails before entering the live session.
          </p>
        </div>

        {/* Hardware Devices Card */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Microphone Test Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className={`p-2 rounded-xl ${micActive ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                  <Mic className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Microphone Input</h4>
                  <p className="text-[11px] text-slate-400">
                    {micPermissionDenied ? 'Using Simulated Audio Input' : 'Live Web Audio Stream Active'}
                  </p>
                </div>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${micActive ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'}`}>
                {micActive ? 'Ready' : 'Checking'}
              </span>
            </div>

            {/* Volume Meter Bar */}
            <div className="space-y-1.5 pt-2">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Input Level</span>
                <span className="font-mono">{micVolume}%</span>
              </div>
              <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800 flex items-center">
                <div
                  className="h-full rounded-full transition-all duration-75 bg-gradient-to-r from-emerald-500 via-teal-400 to-indigo-500"
                  style={{ width: `${Math.max(5, micVolume)}%` }}
                />
              </div>
              <p className="text-[11px] text-slate-500 italic">
                Speak into your mic to observe the volume response.
              </p>
            </div>
          </div>

          {/* Speaker Sound Test Card */}
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm space-y-3 flex flex-col justify-between">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className={`p-2 rounded-xl ${speakerTested ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-slate-400'}`}>
                  {speakerTested ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-white">Speaker Output</h4>
                  <p className="text-[11px] text-slate-400">Check you can hear SkillHunt AI clearly</p>
                </div>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${speakerTested ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30' : 'bg-slate-800 text-slate-400'}`}>
                {speakerTested ? 'Tested' : 'Pending'}
              </span>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={handleTestSpeaker}
                disabled={isPlayingAudio}
                className="w-full py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center justify-center space-x-2 border border-slate-700 transition-colors cursor-pointer"
              >
                {isPlayingAudio ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                    <span>Playing Test Tone...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 text-indigo-400 fill-indigo-400" />
                    <span>Play Audio Test Sound</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Guardrail & Interview Guidelines Overview */}
        <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800/80 backdrop-blur-sm">
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-3">
            <ShieldCheck className="w-4 h-4" />
            <span>Interview Guardrails & Assessment Rules</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-start space-x-2.5">
              <Clock className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">20-Second Hold Policy</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  If asked to hold, SkillHunt AI will hold for up to 20 seconds before prompting to resume or reschedule.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-start space-x-2.5">
              <Globe className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Strict English-Only</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Hindi, Tamil, or non-English speech will trigger an automatic prompt requesting English.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-start space-x-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">3-Question Lifecycle</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  Assessment covers exactly 3 technical questions with up to 1 deep-dive follow-up each.
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/80 flex items-start space-x-2.5">
              <RotateCcw className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-200">Repeat Question Limit</p>
                <p className="text-slate-400 text-[11px] mt-0.5">
                  You may request a question to be repeated up to 2 times before the agent moves forward.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Final CTA */}
        <div className="flex justify-end pt-2">
          <button
            type="button"
            disabled={isPreparingSession}
            onClick={handleStartSession}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-xl shadow-indigo-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            {isPreparingSession ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Connecting to SkillHunt AI Session...</span>
              </>
            ) : (
              <>
                <span>Enter Live Interview Room</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
