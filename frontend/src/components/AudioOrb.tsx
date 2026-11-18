import React, { useEffect, useState } from 'react';
import type { AgentStatus } from '../types';
import { Mic, Volume2, Sparkles, PauseCircle } from 'lucide-react';

interface AudioOrbProps {
  status: AgentStatus;
  holdSecondsLeft?: number;
  audioLevel?: number; // 0 to 1
}

export const AudioOrb: React.FC<AudioOrbProps> = ({
  status,
  holdSecondsLeft = 60,
  audioLevel = 0.4
}) => {
  const [pulseScale, setPulseScale] = useState(1);

  // Dynamic animation based on status and simulated/real audio level
  useEffect(() => {
    const interval = setInterval(() => {
      if (status === 'speaking') {
        setPulseScale(1 + Math.random() * 0.18 + audioLevel * 0.15);
      } else if (status === 'listening') {
        setPulseScale(0.98 + Math.random() * 0.08 + audioLevel * 0.2);
      } else if (status === 'thinking') {
        setPulseScale(0.95 + Math.random() * 0.05);
      } else {
        // on_hold
        setPulseScale(0.92);
      }
    }, 120);

    return () => clearInterval(interval);
  }, [status, audioLevel]);

  // Status visual configurations
  const config = {
    listening: {
      gradient: 'from-emerald-500 via-teal-400 to-cyan-500',
      ringColor: 'border-emerald-400/40',
      outerGlow: 'rgba(16, 185, 129, 0.35)',
      badgeBg: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      label: 'Listening to Candidate...',
      icon: <Mic className="w-4 h-4 animate-pulse text-emerald-400" />
    },
    speaking: {
      gradient: 'from-indigo-500 via-purple-500 to-pink-500',
      ringColor: 'border-indigo-400/50',
      outerGlow: 'rgba(99, 102, 241, 0.45)',
      badgeBg: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
      label: 'SkillHunt AI is Speaking...',
      icon: <Volume2 className="w-4 h-4 animate-bounce text-indigo-400" />
    },
    thinking: {
      gradient: 'from-amber-400 via-orange-500 to-rose-500',
      ringColor: 'border-amber-400/40',
      outerGlow: 'rgba(245, 158, 11, 0.35)',
      badgeBg: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
      label: 'Evaluating & Formulating...',
      icon: <Sparkles className="w-4 h-4 animate-spin text-amber-400" />
    },
    on_hold: {
      gradient: 'from-yellow-500 via-amber-600 to-orange-600',
      ringColor: 'border-yellow-400/60',
      outerGlow: 'rgba(234, 179, 8, 0.4)',
      badgeBg: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
      label: `On Hold (${holdSecondsLeft}s remaining)`,
      icon: <PauseCircle className="w-4 h-4 text-yellow-400 animate-pulse" />
    }
  }[status];

  return (
    <div className="flex flex-col items-center justify-center p-6 select-none">
      {/* Visualizer Container */}
      <div className="relative flex items-center justify-center w-64 h-64 md:w-72 md:h-72">
        {/* Ambient Outer Aura Glow */}
        <div
          className="absolute inset-0 rounded-full blur-3xl transition-all duration-700 pointer-events-none"
          style={{
            background: config.outerGlow,
            transform: `scale(${pulseScale * 1.3})`
          }}
        />

        {/* Outer Pulsing Wave Rings */}
        <div
          className={`absolute inset-0 rounded-full border-2 ${config.ringColor} transition-transform duration-300`}
          style={{
            transform: `scale(${pulseScale * 1.15})`,
            opacity: status === 'on_hold' ? 0.3 : 0.6
          }}
        />
        <div
          className={`absolute inset-4 rounded-full border border-dashed ${config.ringColor} transition-transform duration-500`}
          style={{
            transform: `scale(${pulseScale * 1.08}) rotate(${pulseScale * 30}deg)`,
            opacity: 0.4
          }}
        />

        {/* 3D Visualizer Orb Core */}
        <div
          className={`relative w-40 h-40 md:w-44 md:h-44 rounded-full bg-gradient-to-tr ${config.gradient} shadow-2xl flex items-center justify-center transition-all duration-300 cursor-default`}
          style={{
            transform: `scale(${pulseScale})`,
            boxShadow: `0 0 50px 10px ${config.outerGlow}`
          }}
        >
          {/* Internal Glass Highlight */}
          <div className="absolute inset-2 rounded-full bg-gradient-to-b from-white/30 to-transparent pointer-events-none" />

          {/* Central Status Animation */}
          {status === 'on_hold' ? (
            <div className="text-center text-white z-10">
              <span className="text-3xl font-extrabold tracking-wider font-mono">
                {String(Math.floor(holdSecondsLeft / 60)).padStart(2, '0')}:
                {String(holdSecondsLeft % 60).padStart(2, '0')}
              </span>
              <p className="text-xs uppercase tracking-widest text-yellow-200 mt-1 font-semibold">
                Hold Guardrail
              </p>
            </div>
          ) : (
            <div className="flex space-x-1.5 items-center z-10">
              {[0, 1, 2, 3, 4].map((bar) => (
                <div
                  key={bar}
                  className="w-1.5 bg-white/90 rounded-full transition-all duration-150"
                  style={{
                    height: status === 'speaking'
                      ? `${24 + Math.sin(bar + pulseScale * 10) * 20}px`
                      : status === 'listening'
                      ? `${12 + Math.cos(bar + pulseScale * 5) * 10}px`
                      : '8px'
                  }}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* State Pill Badge */}
      <div className={`mt-4 inline-flex items-center space-x-2 px-4 py-1.5 rounded-full border text-xs font-medium tracking-wide shadow-sm transition-all duration-300 ${config.badgeBg}`}>
        {config.icon}
        <span>{config.label}</span>
      </div>
    </div>
  );
};
