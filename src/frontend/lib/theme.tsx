'use client';

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from 'react';
import { api, ThemePreference } from './api';

type Theme = ThemePreference;

interface ThemeContextType {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  isLoading: boolean;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light');
  const [mounted, setMounted] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  // Get system preference
  const getSystemTheme = (): 'light' | 'dark' => {
    if (typeof window === 'undefined') return 'light';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  };

  // Fetch theme from server if logged in
  const fetchServerTheme = useCallback(async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (!token) {
        setIsLoggedIn(false);
        setIsLoading(false);
        return null;
      }
      
      setIsLoggedIn(true);
      api.setToken(token);
      const settings = await api.getSettings();
      return settings.theme_preference;
    } catch (error) {
      // User not logged in or error fetching settings
      setIsLoggedIn(false);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initialize theme from localStorage first, then server
  useEffect(() => {
    const initTheme = async () => {
      // First, check localStorage for immediate response
      const stored = localStorage.getItem('theme') as Theme | null;
      if (stored && ['light', 'dark', 'system'].includes(stored)) {
        setThemeState(stored);
      }

      // Then try to fetch from server
      const serverTheme = await fetchServerTheme();
      if (serverTheme && ['light', 'dark', 'system'].includes(serverTheme)) {
        setThemeState(serverTheme);
        localStorage.setItem('theme', serverTheme);
      }

      setMounted(true);
    };

    initTheme();
  }, [fetchServerTheme]);

  // Update resolved theme and apply to document
  useEffect(() => {
    const resolved = theme === 'system' ? getSystemTheme() : theme;
    setResolvedTheme(resolved);

    // Apply dark class to html element
    if (resolved === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  // Listen for system theme changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') {
        const resolved = getSystemTheme();
        setResolvedTheme(resolved);
        if (resolved === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    };

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [theme]);

  // Listen for auth changes to re-fetch theme
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'auth_token') {
        fetchServerTheme().then((serverTheme) => {
          if (serverTheme && ['light', 'dark', 'system'].includes(serverTheme)) {
            setThemeState(serverTheme);
            localStorage.setItem('theme', serverTheme);
          }
        });
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [fetchServerTheme]);

  const setTheme = useCallback(async (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);

    // Sync to server if logged in
    if (isLoggedIn) {
      try {
        await api.updateThemePreference(newTheme);
      } catch (error) {
        console.error('Failed to save theme preference to server:', error);
        // Still keep the local preference even if server sync fails
      }
    }
  }, [isLoggedIn]);

  // Prevent flash during hydration
  if (!mounted) {
    return (
      <ThemeContext.Provider value={{ theme: 'system', resolvedTheme: 'light', setTheme: () => {}, isLoading: true }}>
        {children}
      </ThemeContext.Provider>
    );
  }

  return (
    <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme, isLoading }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
