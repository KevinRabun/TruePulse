/**
 * Authentication Context and Hook for TruePulse
 * 
 * TruePulse uses passkey-only authentication - no passwords.
 * Login is handled via WebAuthn passkeys for maximum security.
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, UserProfile, RegisterRequest } from './api';

interface AuthContextType {
  user: UserProfile | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setUser: (user: UserProfile | null) => void;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    try {
      const profile = await api.getProfile();
      setUser(profile);
    } catch {
      setUser(null);
      api.setToken(null);
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      const token = typeof window !== 'undefined' 
        ? localStorage.getItem('access_token') 
        : null;
      
      if (token) {
        try {
          await refreshUser();
        } catch {
          // Token invalid, clear it
          api.setToken(null);
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, [refreshUser]);

  const register = async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      const response = await api.register(data);
      setUser(response.user);
      // Send verification email automatically after registration
      try {
        await api.sendVerificationEmail(data.email);
      } catch {
        // Don't fail registration if email send fails - user can resend later
        console.warn('Failed to send verification email');
      }
      // After registration, redirect to setup passkey
      router.push('/setup-passkey');
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        setUser,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Higher-order component for protected routes
export function withAuth<P extends object>(
  WrappedComponent: React.ComponentType<P>
) {
  return function WithAuthComponent(props: P) {
    const { isAuthenticated, isLoading } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        router.push('/login');
      }
    }, [isLoading, isAuthenticated, router]);

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      );
    }

    if (!isAuthenticated) {
      return null;
    }

    return <WrappedComponent {...props} />;
  };
}
