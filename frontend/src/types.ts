export type Screen = 'login' | 'dashboard' | 'lobby' | 'interview' | 'summary';

export type ProficiencyLevel = 'Beginner' | 'Intermediate' | 'Expert';

export interface User {
  name: string;
  email: string;
  avatarUrl?: string;
  role: string;
}

export interface ResumeData {
  fileName: string;
  candidateName: string;
  title: string;
  experienceYears: number;
  extractedSkills: string[];
  skillsByCategory?: Record<string, string[]>;
  skillsSectionFound?: boolean;
  summary: string;
  rawTextLength?: number;
}

export interface InterviewConfig {
  candidateName: string;
  selectedSkill: string;
  proficiency: ProficiencyLevel;
  resume?: ResumeData;
  targetRole: string;
}

export type AgentStatus = 'listening' | 'speaking' | 'thinking' | 'on_hold';

export interface TranscriptMessage {
  id: string;
  sender: 'skillhunt' | 'vani' | 'candidate' | 'system';
  text: string;
  timestamp: string;
  isQuestion?: boolean;
  questionNumber?: number;
  guardrailBadge?: string;
}

export interface Scorecard {
  persistenceId: string;
  candidateName: string;
  skill: string;
  proficiency: ProficiencyLevel;
  duration: string;
  overallScore: number;
  metrics: {
    label: string;
    score: number;
    description: string;
  }[];
  strengths: string[];
  growthAreas: string[];
  recommendation: 'Strong Hire' | 'Hire' | 'Neutral' | 'Reject';
  questionsCompleted: number;
  totalQuestions: number;
}
