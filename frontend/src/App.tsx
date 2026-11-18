import { useState } from 'react';
import type { Screen, User, InterviewConfig, Scorecard } from './types';
import { LoginView } from './components/LoginView';
import { ResumeDashboardView } from './components/ResumeDashboardView';
import { HardwareLobbyView } from './components/HardwareLobbyView';
import { LiveInterviewView } from './components/LiveInterviewView';
import { InterviewSummaryView } from './components/InterviewSummaryView';
import { DEMO_USER } from './data/mockData';

export function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [user, setUser] = useState<User | null>(null);
  const [interviewConfig, setInterviewConfig] = useState<InterviewConfig | null>(null);
  const [scorecard, setScorecard] = useState<Scorecard | null>(null);

  // 1. Login
  const handleLoginSuccess = (authenticatedUser: User) => {
    setUser(authenticatedUser);
    setCurrentScreen('dashboard');
  };

  // 2. Logout
  const handleLogout = () => {
    setUser(null);
    setInterviewConfig(null);
    setScorecard(null);
    setCurrentScreen('login');
  };

  // 3. From Dashboard to Lobby
  const handleProceedToLobby = (config: InterviewConfig) => {
    setInterviewConfig(config);
    setCurrentScreen('lobby');
  };

  // 4. From Lobby back to Dashboard
  const handleBackToDashboard = () => {
    setCurrentScreen('dashboard');
  };

  // 5. From Lobby to Live Interview
  const handleEnterInterview = () => {
    setCurrentScreen('interview');
  };

  // 6. From Interview to Summary
  const handleFinishInterview = (completedScorecard: Scorecard) => {
    setScorecard(completedScorecard);
    setCurrentScreen('summary');
  };

  // 7. Restart
  const handleRestart = () => {
    setScorecard(null);
    setCurrentScreen('dashboard');
  };

  return (
    <div className="min-h-screen bg-[#080d1a] text-slate-100 font-sans antialiased selection:bg-indigo-500 selection:text-white">
      {currentScreen === 'login' && (
        <LoginView onLoginSuccess={handleLoginSuccess} />
      )}

      {currentScreen === 'dashboard' && (
        <ResumeDashboardView
          user={user || DEMO_USER}
          onLogout={handleLogout}
          onProceedToLobby={handleProceedToLobby}
        />
      )}

      {currentScreen === 'lobby' && interviewConfig && (
        <HardwareLobbyView
          config={interviewConfig}
          onBack={handleBackToDashboard}
          onEnterInterview={handleEnterInterview}
        />
      )}

      {currentScreen === 'interview' && interviewConfig && (
        <LiveInterviewView
          config={interviewConfig}
          onFinishInterview={handleFinishInterview}
        />
      )}

      {currentScreen === 'summary' && scorecard && (
        <InterviewSummaryView
          scorecard={scorecard}
          onRestart={handleRestart}
        />
      )}
    </div>
  );
}

export default App;
