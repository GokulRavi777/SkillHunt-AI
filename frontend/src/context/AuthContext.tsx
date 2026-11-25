import React, { createContext, useContext, useState, useEffect } from 'react';
import { Candidate } from '../types';
import { authService } from '../services/api';

interface AuthContextType {
  candidate: Candidate | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('vani_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchUser = async () => {
      if (token) {
        try {
          const user = await authService.getMe();
          setCandidate(user);
        } catch (err) {
          localStorage.removeItem('vani_token');
          setToken(null);
          setCandidate(null);
        }
      }
      setLoading(false);
    };
    fetchUser();
  }, [token]);

  const login = async (email: string, password: string) => {
    const data = await authService.login(email, password);
    localStorage.setItem('vani_token', data.access_token);
    setToken(data.access_token);
    setCandidate({
      id: data.candidate_id,
      name: data.name,
      email: data.email,
    });
  };

  const logout = () => {
    localStorage.removeItem('vani_token');
    setToken(null);
    setCandidate(null);
  };

  return (
    <AuthContext.Provider value={{ candidate, token, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
