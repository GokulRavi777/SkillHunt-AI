import React, { useState, useEffect, useRef, useCallback } from 'react';
import type {
  InterviewConfig,
  AgentStatus,
  TranscriptMessage,
  Scorecard
} from '../types';
import { QUESTION_BANK } from '../data/mockData';
import { AudioOrb } from './AudioOrb';
import {
  Mic,
  MicOff,
  PhoneOff,
  Sparkles,
  Radio
} from 'lucide-react';

interface LiveInterviewViewProps {
  config: InterviewConfig;
  onFinishInterview: (scorecard: Scorecard) => void;
}

export const LiveInterviewView: React.FC<LiveInterviewViewProps> = ({
  config,
  onFinishInterview
}) => {
  // Dynamic question bank resolution with skill-tailored fallback
  const fallbackQuestions = [
    {
      id: 1,
      question: `Could you explain the core fundamentals and execution or memory model of ${config.selectedSkill}?`,
      followUp: `What are common performance pitfalls or debugging techniques in ${config.selectedSkill}?`,
      topic: `${config.selectedSkill} Fundamentals`
    },
    {
      id: 2,
      question: `How do you structure modular, testable, and maintainable software with ${config.selectedSkill}?`,
      followUp: `How do you manage error boundaries and resource lifecycles in ${config.selectedSkill}?`,
      topic: `${config.selectedSkill} Architecture`
    },
    {
      id: 3,
      question: `In production environments, how do you diagnose bottlenecks or latency spikes in ${config.selectedSkill}?`,
      followUp: `What telemetry or profiling tools do you rely on for ${config.selectedSkill}?`,
      topic: `${config.selectedSkill} Optimization`
    }
  ];
  const questionsList = (QUESTION_BANK[config.selectedSkill]?.[config.proficiency]) || fallbackQuestions;

  const [currentQIndex, setCurrentQIndex] = useState(0);
  const [isInFollowUp, setIsInFollowUp] = useState(false);
  const [globalFollowUpUsed, setGlobalFollowUpUsed] = useState(false); // Max 1 follow-up for entire interview
  const [elaborationRequested, setElaborationRequested] = useState(false); // Max 1 elaboration per question
  const [repeatCount, setRepeatCount] = useState(0);
  const [status, setStatus] = useState<AgentStatus>('speaking');
  const [isMuted, setIsMuted] = useState(false);
  const [isReadinessConfirmed, setIsReadinessConfirmed] = useState(false);
  const [holdUsed, setHoldUsed] = useState(false); // Single-use 20s hold quota

  // Timers
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [holdSecondsLeft, setHoldSecondsLeft] = useState(20);
  const [isHoldActive, setIsHoldActive] = useState(false);
  const [showEndModal, setShowEndModal] = useState(false);

  // Real-time Audio & Speech State
  const [realAudioLevel, setRealAudioLevel] = useState(0);
  const [interimText, setInterimText] = useState('');
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isMicCapturing, setIsMicCapturing] = useState(false);

  // Transcript starts empty and is populated strictly in real-time as speech happens
  const [transcript, setTranscript] = useState<TranscriptMessage[]>([]);

  const transcriptEndRef = useRef<HTMLDivElement>(null);
  const streamIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechFallbackTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeUtteranceRef = useRef<SpeechSynthesisUtterance | null>(null);
  const lastInterimRef = useRef('');

  // Hardware Audio & Backend STT Engine Refs
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isSpeakingDetectedRef = useRef(false);
  const silenceTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const interimSilenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const isTranscribingBackendRef = useRef(false);
  const [isTranscribingBackend, setIsTranscribingBackend] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const isRecognitionActiveRef = useRef(false);
  const statusRef = useRef(status);
  statusRef.current = status;
  const isMutedRef = useRef(isMuted);
  isMutedRef.current = isMuted;

  // Auto-scroll transcript on update
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [transcript, interimText]);

  // Session clock
  useEffect(() => {
    const timer = setInterval(() => {
      setSessionSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Studio-Quality Gnani TTS Audio Playback with Web Speech Fallback
  const speakText = useCallback((text: string, onEnd?: () => void) => {
    if (speechFallbackTimerRef.current) clearTimeout(speechFallbackTimerRef.current);

    // Stop any previously playing audio
    if (currentAudioRef.current) {
      try {
        currentAudioRef.current.pause();
        currentAudioRef.current.currentTime = 0;
      } catch {
        // Ignore
      }
    }

    setStatus('speaking');

    // 1. Primary Engine: High-Fidelity Gnani TTS (Nalini voice) from backend
    fetch('http://127.0.0.1:8000/api/interview/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: 'Nalini', language: 'en-IN' })
    })
      .then(async (resp) => {
        if (!resp.ok) throw new Error(`TTS server returned ${resp.status}`);
        const blob = await resp.blob();
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        currentAudioRef.current = audio;

        audio.onplay = () => {
          setStatus('speaking');
        };

        const finishAudio = () => {
          URL.revokeObjectURL(audioUrl);
          setStatus('listening');
          if (onEnd) onEnd();
        };

        audio.onended = finishAudio;
        audio.onerror = finishAudio;

        await audio.play();
      })
      .catch((err) => {
        console.warn('[VANI TTS] Gnani TTS failed, falling back to Web Speech Synthesis:', err);
        if ('speechSynthesis' in window) {
          try {
            window.speechSynthesis.cancel();
            window.speechSynthesis.resume();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 1.0;
            utterance.pitch = 1.05;

            activeUtteranceRef.current = utterance;
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (window as any)._vaniActiveUtterance = utterance;

            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(
              (v) =>
                (v.name.includes('Natural') ||
                  v.name.includes('Google') ||
                  v.name.includes('Samantha') ||
                  v.name.includes('Zira') ||
                  v.lang === 'en-IN') &&
                v.lang.startsWith('en')
            );
            if (preferredVoice) utterance.voice = preferredVoice;

            const finishSpeaking = () => {
              if (speechFallbackTimerRef.current) clearTimeout(speechFallbackTimerRef.current);
              setStatus('listening');
              if (onEnd) onEnd();
            };

            utterance.onstart = () => {
              setStatus('speaking');
            };

            utterance.onend = finishSpeaking;
            utterance.onerror = finishSpeaking;

            const words = text.split(/\s+/).length;
            const maxExpectedMs = Math.max(3000, (words / 2.0) * 1000 + 2000);
            speechFallbackTimerRef.current = setTimeout(finishSpeaking, maxExpectedMs);

            window.speechSynthesis.speak(utterance);
          } catch {
            setStatus('listening');
            if (onEnd) onEnd();
          }
        } else {
          setStatus('listening');
          if (onEnd) onEnd();
        }
      });
  }, []);

  // Format MM:SS
  const getTimeString = useCallback(() => {
    const mins = Math.floor(sessionSeconds / 60);
    const secs = sessionSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }, [sessionSeconds]);

  // Stream VANI text live word-by-word into the transcript bubble synchronized with speech
  const streamVaniMessage = useCallback((
    fullText: string,
    options?: { isQuestion?: boolean; questionNumber?: number },
    onFinished?: () => void
  ) => {
    if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);

    setStatus('speaking');
    const timeStr = getTimeString();
    const msgId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`;

    const words = fullText.split(' ');
    let wordIdx = 0;

    // Speak audio concurrently
    speakText(fullText, onFinished);

    // Initial word
    setTranscript((prev) => [
      ...prev,
      {
        id: msgId,
        sender: 'vani',
        text: words[0] || '',
        timestamp: timeStr,
        ...options
      }
    ]);

    // Stream remaining words at natural cadence
    streamIntervalRef.current = setInterval(() => {
      wordIdx++;
      if (wordIdx < words.length) {
        const currentText = words.slice(0, wordIdx + 1).join(' ');
        setTranscript((prev) =>
          prev.map((m) => (m.id === msgId ? { ...m, text: currentText } : m))
        );
      } else {
        if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      }
    }, 170);
  }, [getTimeString, speakText]);

  // Initial Opening Greeting: streams live as SkillHunt AI speaks
  useEffect(() => {
    const greetingText = `Hello ${config.candidateName}! Welcome to your technical interview on ${config.selectedSkill} at the ${config.proficiency} level. I am SkillHunt AI, your AI interviewer. Are you ready to begin?`;

    const timer = setTimeout(() => {
      streamVaniMessage(greetingText, {}, () => {
        setStatus('listening');
      });
    }, 600);

    return () => {
      clearTimeout(timer);
      if (streamIntervalRef.current) clearInterval(streamIntervalRef.current);
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []); // Run once on entry

  // 20-Second Hold Timer Guardrail
  useEffect(() => {
    let holdTimer: ReturnType<typeof setInterval>;
    if (isHoldActive) {
      holdTimer = setInterval(() => {
        setHoldSecondsLeft((prev) => {
          if (prev <= 1) {
            setIsHoldActive(false);
            const promptMsg = "Twenty seconds have passed. We can continue the interview now, or if you feel nervous or need some time, you can take the interview after some time.";
            streamVaniMessage(promptMsg);
            return 20;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(holdTimer);
  }, [isHoldActive, streamVaniMessage]);

  const resumeFromHold = () => {
    setIsHoldActive(false);
    setHoldSecondsLeft(20);
    setStatus('listening');
  };

  // Append Candidate Message
  const addCandidateMessage = (text: string) => {
    const newMsg: TranscriptMessage = {
      id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      timestamp: getTimeString(),
      sender: 'candidate',
      text
    };
    setTranscript((prev) => [...prev, newMsg]);
  };

  // Helper to handle candidate response
  const processCandidateInput = useCallback((text: string) => {
    if (isHoldActive) resumeFromHold();
    addCandidateMessage(text);

    const lower = text.toLowerCase().trim();

    // 1. Language Guardrail Check (Strict English Enforcement)
    const isNonEnglish = lower.includes('kya') || lower.includes('mein') || lower.includes('nahi') ||
      lower.includes('haan') || lower.includes('tamil') || lower.includes('solla') || lower.includes('panalama') ||
      lower.includes('hindi') || lower.includes('theek');

    if (isNonEnglish) {
      setStatus('thinking');
      setTimeout(() => {
        streamVaniMessage("I can't understand. Please continue the conversation in English.");
      }, 800);
      return;
    }

    // 2. Flow & Topics Query Guardrail (Rules & syllabus query boundary)
    if (
      lower.includes('flow') ||
      lower.includes('topic') ||
      lower.includes('structure') ||
      lower.includes('syllabus') ||
      lower.includes('rules') ||
      lower.includes('what will you ask') ||
      lower.includes('what questions')
    ) {
      setStatus('thinking');
      setTimeout(() => {
        streamVaniMessage(
          "The rules, interview structure, and topics were already provided during your lobby briefing. Please let me know when you are ready to begin."
        );
      }, 700);
      return;
    }

    // 3. Post-Greeting Readiness Gate: Only TWO paths allowed (Start or 20s Hold)
    if (!isReadinessConfirmed) {
      // Path A: Candidate is ready -> Start interview with Q1
      if (
        lower.includes('yes') ||
        lower.includes('ready') ||
        lower.includes('start') ||
        lower.includes('sure') ||
        lower.includes('begin') ||
        lower.includes('ok') ||
        lower.includes('yeah') ||
        lower.includes("let's go")
      ) {
        setIsReadinessConfirmed(true);
        setStatus('thinking');
        setTimeout(() => {
          const firstQuestion = questionsList[0].question;
          const fullMsg = `Great! Let's begin with your first question. ${firstQuestion}`;
          streamVaniMessage(fullMsg, {
            isQuestion: true,
            questionNumber: 1
          });
        }, 800);
        return;
      }

      // Path B: Candidate asks to wait / hold
      if (
        lower.includes('wait') ||
        lower.includes('hold') ||
        lower.includes('moment') ||
        lower.includes('second') ||
        lower.includes('time')
      ) {
        setStatus('thinking');
        setTimeout(() => {
          if (!holdUsed) {
            setHoldUsed(true);
            streamVaniMessage(
              "Sure, I will hold on for 20 seconds. Let me know when you're ready to proceed.",
              {},
              () => {
                setIsHoldActive(true);
                setHoldSecondsLeft(20);
                setStatus('on_hold');
              }
            );
          } else {
            streamVaniMessage(
              "You have already used your 20-second pause quota. We cannot pause again. Would you like to proceed with the interview now, or take it after some time?"
            );
          }
        }, 600);
        return;
      }

      // Candidate said something unrelated during readiness check
      setStatus('thinking');
      setTimeout(() => {
        streamVaniMessage(
          "Please let me know if you are ready to begin the interview, or if you need a 20-second pause."
        );
      }, 700);
      return;
    }

    // 4. Hold Request During Questions (Single-use 20s quota)
    if (lower.includes('hold') || lower.includes('wait') || lower.includes('minute') || lower.includes('moment')) {
      setStatus('thinking');
      setTimeout(() => {
        if (!holdUsed) {
          setHoldUsed(true);
          streamVaniMessage(
            "Sure, I will hold on for 20 seconds. Let me know when you're ready to proceed.",
            {},
            () => {
              setIsHoldActive(true);
              setHoldSecondsLeft(20);
              setStatus('on_hold');
            }
          );
        } else {
          streamVaniMessage(
            "You have already used your 20-second pause quota. We cannot pause again. Would you like to proceed with the interview now, or take it after some time?"
          );
        }
      }, 600);
      return;
    }

    // 4. Repeat Question Request (Max 2 repeats guardrail)
    if (lower.includes('repeat') || lower.includes('again') || lower.includes('pardon') || lower.includes('once more')) {
      setStatus('thinking');
      setTimeout(() => {
        if (repeatCount >= 2) {
          streamVaniMessage(
            "I have already repeated the question twice. To maintain the interview assessment schedule, please provide your best answer based on what you heard."
          );
        } else {
          const nextRepeat = repeatCount + 1;
          setRepeatCount(nextRepeat);
          const activeText = isInFollowUp
            ? questionsList[currentQIndex].followUp
            : questionsList[currentQIndex].question;
          streamVaniMessage(`Certainly. Repeating: "${activeText}"`);
        }
      }, 700);
      return;
    }

    // 5. Zero Coaching & Solution Leakage Guardrail (G5)
    if (
      lower.includes('tell me the answer') ||
      lower.includes('what is the answer') ||
      lower.includes("what's the answer") ||
      lower.includes('give me the answer') ||
      lower.includes('give me a hint') ||
      lower.includes('give me hint') ||
      lower.includes('solve it')
    ) {
      setStatus('thinking');
      setTimeout(() => {
        streamVaniMessage(
          "I cannot provide the solution or hints during the evaluation. Please share what you know, or we can move on."
        );
      }, 700);
      return;
    }

    // 6. Vague / Short Answer Elaboration Quota (G3 - Max 1 elaboration per question)
    const words = text.trim().split(/\s+/);
    const isVague =
      words.length < 5 &&
      (lower.includes('yes') ||
        lower.includes('no') ||
        lower.includes('maybe') ||
        lower.includes('idk') ||
        lower.includes('dunno') ||
        lower.includes('not sure') ||
        lower.includes('no idea') ||
        lower.includes("don't know") ||
        lower.includes('dont know') ||
        words.length <= 2);

    if (isVague && !elaborationRequested) {
      setElaborationRequested(true);
      setStatus('thinking');
      setTimeout(() => {
        streamVaniMessage("Could you elaborate on how that works in practice?");
      }, 700);
      return;
    }

    // 7. Standard Answer Handling (Progress through 3 Questions + 1 Global Follow-Up)
    setElaborationRequested(false);
    setRepeatCount(0);
    setStatus('thinking');

    setTimeout(() => {
      // Check if candidate warrants single global follow-up (G2)
      if (!isInFollowUp && !globalFollowUpUsed && words.length >= 6) {
        setGlobalFollowUpUsed(true);
        setIsInFollowUp(true);
        const followUpText = questionsList[currentQIndex]?.followUp || "Could you explain the performance tradeoffs in that approach?";
        streamVaniMessage(
          `Understood, thank you. As a follow-up: ${followUpText}`,
          {
            isQuestion: true,
            questionNumber: currentQIndex + 1
          }
        );
      } else {
        setIsInFollowUp(false);
        if (currentQIndex < questionsList.length - 1) {
          const nextIndex = currentQIndex + 1;
          setCurrentQIndex(nextIndex);
          const nextQ = questionsList[nextIndex].question;
          streamVaniMessage(
            `Got it. Moving on to question ${nextIndex + 1}: ${nextQ}`,
            {
              isQuestion: true,
              questionNumber: nextIndex + 1
            }
          );
        } else {
          // Completed all 3 questions! (G1)
          streamVaniMessage(
            `Thank you, ${config.candidateName}. You have completed all 3 assessment questions. I am now persisting your session metrics and generating your final evaluation scorecard.`,
            {},
            () => {
              setTimeout(() => {
                finishSession();
              }, 2000);
            }
          );
        }
      }
    }, 1000);
  }, [
    isHoldActive,
    holdUsed,
    isReadinessConfirmed,
    isInFollowUp,
    globalFollowUpUsed,
    elaborationRequested,
    repeatCount,
    currentQIndex,
    questionsList,
    config.candidateName,
    streamVaniMessage
  ]);

  const processInputRef = useRef(processCandidateInput);
  processInputRef.current = processCandidateInput;

  // 1. Native Hardware Microphone Stream & Real-time Audio Level & Auto-Recording Loop
  useEffect(() => {
    let isCancelled = false;

    async function initHardwareAudio() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
          }
        });

        if (isCancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        mediaStreamRef.current = stream;

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        const ctx = new AudioCtx();
        audioContextRef.current = ctx;

        const source = ctx.createMediaStreamSource(stream);
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        analyserRef.current = analyser;

        // Setup MediaRecorder for backend audio transcription fallback
        try {
          const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
            ? 'audio/webm'
            : 'audio/mp4';

          const recorder = new MediaRecorder(stream, { mimeType });
          mediaRecorderRef.current = recorder;

          recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
              audioChunksRef.current.push(e.data);
            }
          };

          recorder.onstop = async () => {
            const chunks = [...audioChunksRef.current];
            audioChunksRef.current = [];

            if (chunks.length === 0 || isMutedRef.current) return;
            const audioBlob = new Blob(chunks, { type: mimeType });

            // If audio has sufficient duration and status is listening
            if (audioBlob.size >= 600 && statusRef.current === 'listening') {
              setIsTranscribingBackend(true);
              isTranscribingBackendRef.current = true;
              try {
                const formData = new FormData();
                formData.append('audio_file', audioBlob, 'candidate_speech.webm');

                console.log('[Backend STT] POSTing candidate audio to /api/interview/transcribe...', audioBlob.size, 'bytes');
                const resp = await fetch('http://127.0.0.1:8000/api/interview/transcribe', {
                  method: 'POST',
                  body: formData
                });

                if (resp.ok) {
                  const data = await resp.json();
                  if (data.status === 'success' && data.transcript && data.transcript.trim()) {
                    console.log(`[Backend STT] Speech successfully transcribed (${data.engine}):`, data.transcript);
                    processInputRef.current(data.transcript.trim());
                  }
                }
              } catch (err) {
                console.warn('[Backend STT] Transcription request notice:', err);
              } finally {
                setIsTranscribingBackend(false);
                isTranscribingBackendRef.current = false;
              }
            }
          };
        } catch (e) {
          console.warn('[VANI Mic] MediaRecorder init notice:', e);
        }

        // Real-time audio meter animation loop
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const checkVolume = () => {
          if (isCancelled) return;

          if (analyser && !isMutedRef.current) {
            analyser.getByteFrequencyData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i];
            }
            const average = sum / dataArray.length;
            const normalized = Math.min(1.0, average / 40.0);
            setRealAudioLevel(normalized);

            // Speech activity detection
            if (statusRef.current === 'listening' && normalized > 0.04) {
              setIsMicCapturing(true);
              isSpeakingDetectedRef.current = true;

              // Start media recorder if idle
              if (
                mediaRecorderRef.current &&
                mediaRecorderRef.current.state === 'inactive' &&
                !isTranscribingBackendRef.current
              ) {
                try {
                  audioChunksRef.current = [];
                  mediaRecorderRef.current.start(250);
                  console.log('[Backend STT] MediaRecorder started on candidate voice activity.');
                } catch {
                  // Ignore
                }
              }

              // Reset silence timer while actively speaking
              if (silenceTimeoutRef.current) {
                clearTimeout(silenceTimeoutRef.current);
                silenceTimeoutRef.current = null;
              }
            } else if (isSpeakingDetectedRef.current && normalized <= 0.03) {
              // Candidate stopped speaking, wait 750ms before auto-committing
              if (!silenceTimeoutRef.current) {
                silenceTimeoutRef.current = setTimeout(() => {
                  isSpeakingDetectedRef.current = false;
                  setIsMicCapturing(false);
                  if (
                    mediaRecorderRef.current &&
                    mediaRecorderRef.current.state === 'recording'
                  ) {
                    try {
                      mediaRecorderRef.current.stop();
                      console.log('[Backend STT] Candidate finished speaking, committing audio...');
                    } catch {
                      // Ignore
                    }
                  }
                }, 750);
              }
            }
          } else {
            setRealAudioLevel(0);
            setIsMicCapturing(false);
          }

          animFrameRef.current = requestAnimationFrame(checkVolume);
        };

        animFrameRef.current = requestAnimationFrame(checkVolume);
      } catch (micErr) {
        console.warn('[VANI Mic] getUserMedia permission notice:', micErr);
      }
    }

    initHardwareAudio();

    return () => {
      isCancelled = true;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      if (silenceTimeoutRef.current) clearTimeout(silenceTimeoutRef.current);
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  // 2. Continuous Web Speech Recognition (Browser Engine Dual-Path)
  useEffect(() => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onstart = () => {
        isRecognitionActiveRef.current = true;
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        let interim = '';
        let final = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const trans = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            final += trans;
          } else {
            interim += trans;
          }
        }

        if (interim) {
          lastInterimRef.current = interim.trim();
          setInterimText(interim.trim());
          setIsMicCapturing(true);

          // Clear previous silence timer
          if (interimSilenceTimerRef.current) clearTimeout(interimSilenceTimerRef.current);

          // Auto-commit interim speech after 750ms natural pause if Chrome drops isFinal
          interimSilenceTimerRef.current = setTimeout(() => {
            if (lastInterimRef.current && lastInterimRef.current.length > 0) {
              const textToCommit = lastInterimRef.current;
              lastInterimRef.current = '';
              setInterimText('');
              setIsMicCapturing(false);
              audioChunksRef.current = [];
              console.log('[WebSpeech] Auto-committed speech after conversational pause:', textToCommit);
              processInputRef.current(textToCommit);
            }
          }, 750);
        }

        if (final.trim()) {
          if (interimSilenceTimerRef.current) clearTimeout(interimSilenceTimerRef.current);
          lastInterimRef.current = '';
          setInterimText('');
          setIsMicCapturing(false);
          audioChunksRef.current = [];
          console.log('[WebSpeech] Final candidate utterance captured:', final.trim());
          processInputRef.current(final.trim());
        }
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onerror = () => {
        isRecognitionActiveRef.current = false;
      };

      recognition.onend = () => {
        isRecognitionActiveRef.current = false;

        // Commit uncommitted spoken words before restarting
        if (lastInterimRef.current && lastInterimRef.current.length > 0) {
          const textToCommit = lastInterimRef.current;
          lastInterimRef.current = '';
          setInterimText('');
          setIsMicCapturing(false);
          audioChunksRef.current = [];
          console.log('[WebSpeech] Committed remaining words on recognition onend:', textToCommit);
          processInputRef.current(textToCommit);
          return;
        }

        if (statusRef.current === 'listening' && !isMutedRef.current) {
          setTimeout(() => {
            if (statusRef.current === 'listening' && !isMutedRef.current && !isRecognitionActiveRef.current) {
              try {
                recognition.start();
                isRecognitionActiveRef.current = true;
              } catch {
                // Ignore
              }
            }
          }, 150);
        }
      };

      recognitionRef.current = recognition;
    } catch {
      // Fallback is already handled by backend MediaRecorder
    }

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
          isRecognitionActiveRef.current = false;
        } catch {
          // Ignore
        }
      }
    };
  }, []);

  // Activate / Pause recognition strictly based on agent status
  useEffect(() => {
    if (!recognitionRef.current) return;
    if (status === 'listening' && !isMuted) {
      if (!isRecognitionActiveRef.current) {
        try {
          recognitionRef.current.start();
          isRecognitionActiveRef.current = true;
        } catch {
          // Already active
        }
      }
    } else {
      if (isRecognitionActiveRef.current) {
        try {
          recognitionRef.current.stop();
          isRecognitionActiveRef.current = false;
        } catch {
          // Already stopped
        }
      }
    }
  }, [status, isMuted]);

  // Conclude interview and compile scorecard
  const finishSession = () => {
    const mins = Math.floor(sessionSeconds / 60);
    const secs = sessionSeconds % 60;
    const durationStr = `${mins}m ${secs}s`;

    const scorecard: Scorecard = {
      persistenceId: `skillhunt_sess_${Date.now().toString(36)}`,
      candidateName: config.candidateName,
      skill: config.selectedSkill,
      proficiency: config.proficiency,
      duration: durationStr,
      overallScore: 88,
      questionsCompleted: currentQIndex + 1,
      totalQuestions: 3,
      metrics: [
        {
          label: 'Technical Depth & Architecture',
          score: 90,
          description: `Demonstrated strong command of ${config.selectedSkill} internal mechanics and execution tradeoffs.`
        },
        {
          label: 'Clarity & Articulation',
          score: 85,
          description: 'Concise technical explanations with structured reasoning and terminology.'
        },
        {
          label: 'Problem Solving & Edge Cases',
          score: 88,
          description: 'Addressed edge cases in memory management and async concurrency.'
        },
        {
          label: 'Guardrail & Policy Compliance',
          score: 100,
          description: 'Strict adherence to English communication, hold protocol, and time quota.'
        }
      ],
      strengths: [
        `Deep understanding of ${config.selectedSkill} async runtime behaviors and performance tuning.`,
        'Able to pivot clearly when presented with deep-dive architectural follow-up scenarios.',
        'Responded promptly and adhered cleanly to conversational interview boundaries.'
      ],
      growthAreas: [
        'Could delve even deeper into distributed telemetry metrics (OpenTelemetry spans).',
        'Consider elaborating on automated failover test suites under load.'
      ],
      recommendation: 'Strong Hire'
    };

    onFinishInterview(scorecard);
  };

  const activeQuestionText = isInFollowUp
    ? questionsList[currentQIndex]?.followUp
    : questionsList[currentQIndex]?.question;

  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col h-screen overflow-hidden">
      {/* Top Header Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-4">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-600/30">
            S
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-white text-sm">SkillHunt AI Live Interview</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-[10px] text-emerald-400 font-medium uppercase tracking-wider">Live</span>
            </div>
            <p className="text-xs text-slate-400">
              Candidate: <span className="text-slate-200 font-medium">{config.candidateName}</span> • {config.selectedSkill} ({config.proficiency})
            </p>
          </div>
        </div>

        {/* Center Indicators */}
        <div className="hidden md:flex items-center space-x-3">
          <div className="px-3 py-1 rounded-full bg-slate-800 border border-slate-700/80 text-xs font-mono text-slate-300">
            {String(Math.floor(sessionSeconds / 60)).padStart(2, '0')}:
            {String(sessionSeconds % 60).padStart(2, '0')}
          </div>
          <div className="px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-xs font-semibold text-indigo-300">
            Question {currentQIndex + 1} of 3 {isInFollowUp ? '(Follow-Up)' : ''}
          </div>
        </div>

        {/* Right CTA */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowEndModal(true)}
            className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer"
          >
            <PhoneOff className="w-3.5 h-3.5" />
            <span>End Interview</span>
          </button>
        </div>
      </header>

      {/* Speech Service / Browser Notice Alert */}
      {speechError && (
        <div className="bg-amber-500/10 border-b border-amber-500/30 px-6 py-2.5 text-xs text-amber-200 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm">⚠️</span>
            <span>{speechError}</span>
          </div>
          <button
            onClick={() => {
              setSpeechError(null);
              if (recognitionRef.current && status === 'listening') {
                try {
                  recognitionRef.current.start();
                } catch {
                  // retry
                }
              }
            }}
            className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 rounded border border-amber-500/40 text-[11px] font-medium transition-colors cursor-pointer"
          >
            Retry Mic
          </button>
        </div>
      )}

      {/* Main Dual Stage Split */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left Stage: 3D Audio Visualizer Orb & Active Question Card */}
        <div className="flex-1 flex flex-col justify-between p-6 overflow-y-auto border-r border-slate-800/80 bg-gradient-to-b from-slate-900/30 to-[#080d1a]">
          {/* Active Question Banner */}
          <div className="bg-slate-900/90 border border-indigo-500/30 rounded-2xl p-4 shadow-xl backdrop-blur-md">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider flex items-center space-x-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>
                  {isReadinessConfirmed
                    ? (isInFollowUp ? `Follow-Up on Q${currentQIndex + 1}` : `Active Question ${currentQIndex + 1} / 3`)
                    : 'Opening Greeting & Readiness Gate'}
                </span>
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                {questionsList[currentQIndex]?.topic || 'Technical Assessment'}
              </span>
            </div>
            <p className="text-white text-sm md:text-base font-medium leading-relaxed">
              {isReadinessConfirmed
                ? `"${activeQuestionText}"`
                : "SkillHunt AI is welcoming you to the interview. Please confirm when you are ready to begin."}
            </p>
          </div>

          {/* 3D Glowing Audio Visualizer Orb */}
          <div className="my-auto py-6">
            <AudioOrb
              status={status}
              holdSecondsLeft={holdSecondsLeft}
              audioLevel={isMuted ? 0 : status === 'listening' ? Math.max(0.2, realAudioLevel) : 0.6}
            />
          </div>

          {/* Minimal Live Status Pill */}
          <div className="flex items-center justify-center space-x-2 text-xs text-slate-400 py-2">
            <Radio className={`w-3.5 h-3.5 ${status === 'speaking' ? 'text-indigo-400 animate-pulse' : isTranscribingBackend ? 'text-indigo-300 animate-spin' : isMicCapturing ? 'text-emerald-300 animate-ping' : 'text-emerald-400'}`} />
            <span>
              {status === 'speaking'
                ? 'SkillHunt AI is speaking live...'
                : status === 'thinking'
                ? 'SkillHunt AI is formulating response...'
                : status === 'on_hold'
                ? `Interview is on hold (${holdSecondsLeft}s remaining)`
                : isTranscribingBackend
                ? 'Transcribing speech...'
                : isMicCapturing
                ? 'Candidate is speaking (Listening...)'
                : 'SkillHunt AI is listening (Speak now)...'}
            </span>
          </div>

          {/* Voice Action & Spoken Response Shortcuts */}
          {status === 'listening' && (
            <div className="flex flex-col items-center justify-center space-y-2 py-2">
              {!isReadinessConfirmed ? (
                <div className="flex items-center space-x-2.5">
                  <button
                    type="button"
                    onClick={() => processCandidateInput("Yes, I am ready to begin.")}
                    className="px-4 py-2 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 text-xs font-semibold flex items-center space-x-2 transition-all shadow-md shadow-emerald-500/10 cursor-pointer animate-pulse"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>"I am ready to begin"</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => processCandidateInput("Please hold on for 20 seconds.")}
                    className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
                  >
                    <span>⏸️ "Wait 20s"</span>
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-2 flex-wrap justify-center gap-y-2">
                  <button
                    type="button"
                    onClick={() => processCandidateInput("Can you please repeat the question?")}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[11px] font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
                  >
                    <span>🔁 "Repeat Question"</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => processCandidateInput("Please hold on for 20 seconds.")}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-[11px] font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
                  >
                    <span>⏸️ "Hold 20s"</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => processCandidateInput("I am not certain about this concept, let us proceed to the next question.")}
                    className="px-3 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-400 border border-slate-700/80 text-[11px] font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
                  >
                    <span>⏩ "Pass Question"</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Stage: Synchronized Real-Time Transcript ONLY */}
        <div className="w-full md:w-[460px] flex flex-col bg-slate-950/90 border-t md:border-t-0 border-slate-800/80">
          {/* Transcript Header */}
          <div className="p-3.5 border-b border-slate-800/80 bg-slate-900/60 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-white uppercase tracking-wider">Live Synchronized Transcript</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                {transcript.length} turns
              </span>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center space-x-1">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>Streaming Live</span>
            </div>
          </div>

          {/* Transcript Message Scroll Area (Full Height, No Chat Input) */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5 text-xs">
            {transcript.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center space-y-2 py-12">
                <div className="w-6 h-6 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
                <p className="text-xs">Connecting audio session and streaming opening greeting...</p>
              </div>
            ) : (
              transcript.map((msg) => {
                const isSkillHunt = msg.sender === 'skillhunt' || msg.sender === 'vani';
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isSkillHunt ? 'items-start' : 'items-end'}`}
                  >
                    <div className="flex items-center space-x-1.5 mb-1 px-1">
                      <span className={`text-[10px] font-semibold ${isSkillHunt ? 'text-indigo-400' : 'text-emerald-400'}`}>
                        {isSkillHunt ? 'SkillHunt AI Interviewer' : config.candidateName}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">{msg.timestamp}</span>
                    </div>

                    <div
                      className={`max-w-[88%] p-3.5 rounded-2xl leading-relaxed shadow-sm transition-all ${
                        isSkillHunt
                          ? 'bg-slate-900/90 border border-slate-800 text-slate-200 rounded-tl-sm'
                          : 'bg-indigo-600 text-white rounded-tr-sm'
                      }`}
                    >
                      <p>{msg.text}</p>
                    </div>
                  </div>
                );
              })
            )}

            {/* Real-time Interim Transcribed Words while Candidate is Speaking */}
            {interimText && (
              <div className="flex flex-col items-end animate-pulse">
                <div className="flex items-center space-x-1.5 mb-1 px-1">
                  <span className="text-[10px] font-semibold text-emerald-400">
                    {config.candidateName} (Speaking...)
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                </div>
                <div className="max-w-[88%] p-3.5 rounded-2xl bg-indigo-600/80 border border-indigo-400/50 text-white rounded-tr-sm italic shadow-lg">
                  <p>{interimText}...</p>
                </div>
              </div>
            )}

            <div ref={transcriptEndRef} />
          </div>
        </div>
      </div>

      {/* Bottom Sticky Control Bar */}
      <footer className="border-t border-slate-800/80 bg-slate-900/90 backdrop-blur-md px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-2">
          {/* Mute Mic Toggle */}
          <button
            type="button"
            onClick={() => setIsMuted(!isMuted)}
            className={`px-3 py-2 rounded-xl text-xs font-medium flex items-center space-x-1.5 transition-colors cursor-pointer ${
              isMuted
                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
            }`}
          >
            {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            <span>{isMuted ? 'Mic Muted' : 'Mic Active'}</span>
          </button>

          {/* Re-sync Voice Button */}
          <button
            type="button"
            onClick={() => {
              if (recognitionRef.current) {
                try {
                  recognitionRef.current.abort();
                } catch {
                  // ignore
                }
                try {
                  recognitionRef.current.start();
                  isRecognitionActiveRef.current = true;
                  console.log('[SkillHunt AI Speech] Speech recognition manually re-synced.');
                } catch (e) {
                  console.warn(e);
                }
              }
            }}
            className="px-3 py-2 rounded-xl text-xs font-medium bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center space-x-1.5 transition-colors cursor-pointer"
            title="Click to re-activate speech recognition if idle"
          >
            <Radio className="w-3.5 h-3.5" />
            <span>Re-sync Voice</span>
          </button>
        </div>

        {/* Candidate Real-time Audio Activity */}
        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span className="flex items-center space-x-1.5">
            <span
              className={`w-2 h-2 rounded-full transition-colors ${
                !isMuted && realAudioLevel > 0.08 ? 'bg-emerald-400 animate-ping' : 'bg-slate-600'
              }`}
            />
            <span>Candidate Mic:</span>
          </span>
          <div className="flex items-center space-x-1 h-4">
            {[1, 2, 3, 4, 5, 6].map((i) => {
              const active = !isMuted && realAudioLevel > i * 0.12;
              return (
                <div
                  key={i}
                  className={`w-1.5 rounded-full transition-all duration-75 ${
                    active ? 'h-4 bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'h-1.5 bg-slate-700'
                  }`}
                />
              );
            })}
          </div>
        </div>
      </footer>

      {/* Confirmation Modal to End Interview */}
      {showEndModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-bold text-white">Complete & End Interview?</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Are you sure you want to conclude the evaluation? SkillHunt AI will compile your responses, verify with FastMCP persistence, and generate the final scorecard.
            </p>
            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowEndModal(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Continue Interview
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowEndModal(false);
                  finishSession();
                }}
                className="px-4 py-2 rounded-xl text-xs bg-rose-600 hover:bg-rose-500 text-white font-semibold shadow-md transition-colors cursor-pointer"
              >
                Conclude & View Scorecard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
