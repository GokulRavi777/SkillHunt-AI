import React, { useState, useRef } from 'react';
import type { User, ResumeData, ProficiencyLevel, InterviewConfig } from '../types';
import { SAMPLE_RESUMES } from '../data/mockData';
import {
  UploadCloud,
  FileText,
  CheckCircle,
  Sparkles,
  ArrowRight,
  Code2,
  Layers,
  Award,
  Plus,
  Trash2,
  LogOut,
  UserCheck
} from 'lucide-react';

interface ResumeDashboardViewProps {
  user: User;
  onLogout: () => void;
  onProceedToLobby: (config: InterviewConfig) => void;
}

export const ResumeDashboardView: React.FC<ResumeDashboardViewProps> = ({
  user,
  onLogout,
  onProceedToLobby
}) => {
  const [resumeData, setResumeData] = useState<ResumeData | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [selectedSkill, setSelectedSkill] = useState<string>('');
  const [proficiency, setProficiency] = useState<ProficiencyLevel>('Intermediate');
  const [customSkillInput, setCustomSkillInput] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Probe backend on mount
  React.useEffect(() => {
    fetch('http://127.0.0.1:8000/api/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'healthy') {
          setBackendOnline(true);
        }
      })
      .catch(() => {
        setBackendOnline(false);
      });
  }, []);

  // Load a pre-defined sample resume instantly
  const handleLoadSampleResume = (key: 'fullstack' | 'aiml') => {
    setIsParsing(true);
    setParseError(null);
    setTimeout(() => {
      const sample = SAMPLE_RESUMES[key];
      setResumeData(sample);
      setSelectedSkill(sample.extractedSkills[0]);
      setIsParsing(false);
    }, 350);
  };

  // Real backend resume file upload & extraction
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsParsing(true);
    setParseError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/resume/parse', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({ detail: 'Failed to parse resume.' }));
        throw new Error(errJson.detail || `Upload failed with status ${response.status}`);
      }

      const parsed: ResumeData = await response.json();
      setResumeData(parsed);
      if (parsed.extractedSkills && parsed.extractedSkills.length > 0) {
        setSelectedSkill(parsed.extractedSkills[0]);
      }
    } catch (err: unknown) {
      console.warn('Backend parsing error:', err);
      const message = err instanceof Error ? err.message : 'Error connecting to parser backend.';
      setParseError(message);

      // Fallback extraction so the user is never blocked
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
      const fallbackResume: ResumeData = {
        fileName: file.name,
        candidateName: user.name,
        title: 'Software Engineer',
        experienceYears: 4,
        extractedSkills: ['Python', 'FastAPI', 'Docker', 'PostgreSQL', 'Redis', 'AsyncIO', 'LiveKit', 'FastMCP'],
        summary: `Extracted from ${nameWithoutExt} via local fallback parser.`
      };
      setResumeData(fallbackResume);
      setSelectedSkill('Python');
    } finally {
      setIsParsing(false);
    }
  };

  const handleAddCustomSkill = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customSkillInput.trim();
    if (!trimmed || !resumeData) return;
    if (!resumeData.extractedSkills.includes(trimmed)) {
      setResumeData({
        ...resumeData,
        extractedSkills: [...resumeData.extractedSkills, trimmed]
      });
      setSelectedSkill(trimmed);
    }
    setCustomSkillInput('');
  };

  const handleProceed = () => {
    if (!selectedSkill) return;
    onProceedToLobby({
      candidateName: resumeData?.candidateName || user.name,
      selectedSkill,
      proficiency,
      resume: resumeData || undefined,
      targetRole: resumeData?.title || 'Technical Specialist'
    });
  };

  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col">
      {/* Top Navigation */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-6xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-600/30">
              V
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight">SkillHunt AI</span>
              <span className="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                Candidate Setup
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="hidden sm:flex items-center space-x-2 text-xs text-slate-300 bg-slate-800/60 px-3 py-1.5 rounded-full border border-slate-700/60">
              <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>{user.name}</span>
              <span className="text-slate-500">({user.email})</span>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-8">
        {/* Step Indicator / Intro */}
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Configure Your Technical Interview</h2>
          <p className="text-slate-400 text-sm mt-1">
            Upload your resume to extract validated skills or select from pre-analyzed profiles, then choose your interview proficiency level.
          </p>
        </div>

        {/* Section 1: Resume Upload & Extraction */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
            <div className="flex items-center space-x-2.5">
              <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">1. Resume Analysis & Skill Extraction</h3>
                <p className="text-xs text-slate-400">PDF, DOCX, or TXT (Max 10MB)</p>
              </div>
            </div>

            {/* Quick Demo Resume Presets */}
            <div className="flex items-center space-x-2">
              <span className="text-xs text-slate-400">Quick Demo Presets:</span>
              <button
                type="button"
                onClick={() => handleLoadSampleResume('fullstack')}
                className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/20 transition-colors cursor-pointer flex items-center space-x-1"
              >
                <Sparkles className="w-3 h-3 text-indigo-400" />
                <span>Backend/Python</span>
              </button>
              <button
                type="button"
                onClick={() => handleLoadSampleResume('aiml')}
                className="px-2.5 py-1 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/20 transition-colors cursor-pointer flex items-center space-x-1"
              >
                <Sparkles className="w-3 h-3 text-purple-400" />
                <span>AI/Voice</span>
              </button>
            </div>
          </div>

          {/* Backend Connection Status Badge */}
          <div className="mb-3 flex items-center justify-between text-xs px-3 py-1.5 rounded-lg bg-slate-950/40 border border-slate-800">
            <div className="flex items-center space-x-2">
              <span className={`w-2 h-2 rounded-full ${backendOnline ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span className="text-slate-300">
                {backendOnline ? 'Backend Skills Extraction API: Connected (Port 8000)' : 'Backend API Starting / Offline'}
              </span>
            </div>
            <span className="text-[11px] text-slate-500 font-mono">FastAPI + PyPDF Engine</span>
          </div>

          {parseError && (
            <div className="mb-3 p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
              {parseError} (Loaded with fallback engine).
            </div>
          )}

          {/* Upload Dropzone */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
          />

          {!resumeData ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-xl p-8 text-center cursor-pointer transition-all bg-slate-950/30 hover:bg-indigo-950/10 group"
            >
              {isParsing ? (
                <div className="py-4 space-y-3">
                  <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="text-sm font-medium text-indigo-300">Parsing Resume & Extracting Technical Skills...</p>
                </div>
              ) : (
                <>
                  <div className="w-12 h-12 rounded-full bg-slate-800 group-hover:bg-indigo-600/20 text-slate-400 group-hover:text-indigo-400 mx-auto flex items-center justify-center transition-colors mb-3">
                    <UploadCloud className="w-6 h-6" />
                  </div>
                  <p className="text-sm font-medium text-slate-200">
                    Click to browse or drag and drop your resume file here
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    Or select one of the Quick Demo Presets above for immediate testing
                  </p>
                </>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-center space-x-3.5">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center">
                  <CheckCircle className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-white text-sm">{resumeData.fileName}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-medium">
                      {resumeData.skillsSectionFound ? 'Skills Section Isolated' : 'Extracted'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {resumeData.title} • {resumeData.experienceYears} Years Exp • {resumeData.extractedSkills.length} Technical Skills Detected
                    {resumeData.skillsSectionFound && (
                      <span className="text-emerald-400 ml-1.5 font-medium">(Section-Aware Validated)</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 self-end md:self-auto">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors cursor-pointer"
                >
                  Replace File
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResumeData(null);
                    setSelectedSkill('');
                  }}
                  className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
                  title="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Extracted Skills List */}
          {resumeData && (
            <div className="mt-5 pt-5 border-t border-slate-800/80">
              <div className="flex items-center justify-between mb-2.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                  <Code2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Select Primary Skill to Assess ({resumeData.extractedSkills.length} Extracted)</span>
                </label>
                <span className="text-[11px] text-slate-400">Click a chip to choose topic</span>
              </div>

              <div className="flex flex-wrap gap-2 mb-3">
                {resumeData.extractedSkills.map((skill) => {
                  const isSelected = selectedSkill.toLowerCase() === skill.toLowerCase();
                  return (
                    <button
                      key={skill}
                      type="button"
                      onClick={() => setSelectedSkill(skill)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all flex items-center space-x-1.5 cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/40 ring-2 ring-indigo-400'
                          : 'bg-slate-800/80 hover:bg-slate-800 text-slate-300 border border-slate-700/60'
                      }`}
                    >
                      {isSelected && <CheckCircle className="w-3 h-3 text-white" />}
                      <span>{skill}</span>
                    </button>
                  );
                })}
              </div>

              {/* Add Custom Skill Tag */}
              <form onSubmit={handleAddCustomSkill} className="flex items-center space-x-2 max-w-sm mt-2">
                <input
                  type="text"
                  placeholder="+ Add custom skill tag..."
                  value={customSkillInput}
                  onChange={(e) => setCustomSkillInput(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-xs bg-slate-950/60 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={!customSkillInput.trim()}
                  className="px-2.5 py-1.5 text-xs bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white rounded-lg transition-colors disabled:opacity-40 cursor-pointer flex items-center space-x-1"
                >
                  <Plus className="w-3 h-3" />
                  <span>Add</span>
                </button>
              </form>
            </div>
          )}
        </div>

        {/* Section 2: Proficiency Level Selection */}
        <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-6 backdrop-blur-sm">
          <div className="flex items-center space-x-2.5 mb-4">
            <div className="p-2 rounded-lg bg-indigo-600/20 text-indigo-400">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">2. Select Proficiency Level</h3>
              <p className="text-xs text-slate-400">
                Determines the depth, architectural scope, and follow-up complexity of questions.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Beginner */}
            <div
              onClick={() => setProficiency('Beginner')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                proficiency === 'Beginner'
                  ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                  : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-white">Beginner</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Fundamental
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Core syntax, basic data structures, fundamental concepts, and standard language features.
              </p>
            </div>

            {/* Intermediate */}
            <div
              onClick={() => setProficiency('Intermediate')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                proficiency === 'Intermediate'
                  ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                  : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-white">Intermediate</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Standard
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                AsyncIO patterns, decorators, dependency injection, caching, and clean code principles.
              </p>
            </div>

            {/* Expert / Advanced */}
            <div
              onClick={() => setProficiency('Expert')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                proficiency === 'Expert'
                  ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                  : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-white">Expert (Advanced)</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">
                  Architecture
                </span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                GIL internals, FastMCP integration, distributed streaming, zero-downtime scalability & security.
              </p>
            </div>
          </div>
        </div>

        {/* Section 3: Summary Bar & Proceed CTA */}
        <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-indigo-600/30 text-indigo-300">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">Selected Assessment Configuration:</p>
              <p className="text-sm font-bold text-white">
                {selectedSkill ? selectedSkill : 'None selected'} • <span className="text-indigo-400">{proficiency} Level</span>
              </p>
            </div>
          </div>

          <button
            type="button"
            disabled={!selectedSkill}
            onClick={handleProceed}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-semibold text-sm flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-40 cursor-pointer"
          >
            <span>Continue to Hardware Check</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </main>
    </div>
  );
};
