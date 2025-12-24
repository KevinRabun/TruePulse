/**
 * Authentication Context and Hook for TruePulse
 * 
 * TruePulse uses passkey-only authentication - no passwords.
 * Login is handled via WebAuthn passkeys for maximum security.
 * 
 * This AuthProvider syncs with the Zustand auth store (useAuthStore)
 * to ensure consistent auth state across the app.
 */

'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api, UserProfile, RegisterRequest } from './api';
import { useAuthStore } from './store';

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
  const [user, setUserState] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  
  // Subscribe to Zustand store changes
  const storeUser = useAuthStore((state) => state.user);
  const storeToken = useAuthStore((state) => state.accessToken);
  const storeClearAuth = useAuthStore((state) => state.clearAuth);

  const refreshUser = useCallback(async () => {
    try {
      const profile = await api.getProfile();
      console.log('[Auth] refreshUser - API returned profile:', {
        username: profile.username,
        display_name: profile.display_name,
        email: profile.email,
      });
      setUserState(profile);
    } catch {
      setUserState(null);
      api.setToken(null);
      storeClearAuth();
    }
  }, [storeClearAuth]);

  // Sync with Zustand store when it changes - only for initial login
  // Don't override if we already have full user data from API
  useEffect(() => {
    if (storeUser && storeToken) {
      // Only set minimal user if we don't have user data yet
      // After refreshUser() runs, user will have full profile data
      if (!user) {
        // Immediately fetch full profile when store has user
        refreshUser();
      }
    } else if (!storeToken) {
      setUserState(null);
    }
  }, [storeUser, storeToken, user, refreshUser]);

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
          storeClearAuth();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, [refreshUser, storeClearAuth]);

  const setUser = (newUser: UserProfile | null) => {
    setUserState(newUser);
  };

  const register = async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      const response = await api.register(data);
      setUserState(response.user);
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
    setUserState(null);
    storeClearAuth();
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
