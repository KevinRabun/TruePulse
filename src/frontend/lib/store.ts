/**
 * Auth Store for TruePulse
 * 
 * Uses Zustand for state management of authentication state.
 * Handles access tokens, refresh tokens, and user profile data.
 * 
 * IMPORTANT: This store syncs with localStorage['access_token'] directly
 * to ensure compatibility with AuthProvider and the API client.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { api } from './api';

interface User {
  id: string;
  email: string;
  username: string;
  display_name?: string;
  isVerified: boolean;
  emailVerified: boolean;
  hasPasskey: boolean;
  passkeyOnly: boolean;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  
  // Actions
  setAccessToken: (token: string | null) => void;
  setRefreshToken: (token: string | null) => void;
  setUser: (user: User | null) => void;
  clearAuth: () => void;
  
  // Derived state helpers
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      
      setAccessToken: (token) => {
        // Sync with the API client and localStorage['access_token']
        // This ensures AuthProvider can pick up the token
        api.setToken(token);
        set({ accessToken: token });
      },
      setRefreshToken: (token) => set({ refreshToken: token }),
      setUser: (user) => set({ user }),
      clearAuth: () => {
        // Clear API token and localStorage['access_token'] as well
        api.setToken(null);
        set({ accessToken: null, refreshToken: null, user: null });
      },
      
      isAuthenticated: () => {
        const state = get();
        return !!state.accessToken && !!state.user;
      },
    }),
    {
      name: 'truepulse-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
);
