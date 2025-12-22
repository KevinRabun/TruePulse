'use client';

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { api } from '@/lib/api';

interface AdEngagement {
  totalViews: number;
  totalClicks: number;
  todayViews: number;
  todayClicks: number;
}

interface AdContextType {
  engagement: AdEngagement;
  trackView: (adType: string, placement: string) => Promise<void>;
  trackClick: (adType: string, placement: string) => Promise<void>;
  isLoading: boolean;
  showPersonalizedAds: boolean;
  setShowPersonalizedAds: (value: boolean) => void;
}

const AdContext = createContext<AdContextType | undefined>(undefined);

const AD_ENGAGEMENT_KEY = 'truepulse_ad_engagement';

export function AdProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [isLoading] = useState(false);
  const [showPersonalizedAds, setShowPersonalizedAds] = useState(false);
  // Initialize engagement from localStorage synchronously
  const [engagement, setEngagement] = useState<AdEngagement>(() => {
    if (typeof window === 'undefined') {
      return {
        totalViews: 0,
        totalClicks: 0,
        todayViews: 0,
        todayClicks: 0,
      };
    }
    const stored = localStorage.getItem(AD_ENGAGEMENT_KEY);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        const today = new Date().toDateString();
        // Reset daily counters if it's a new day
        if (data.date !== today) {
          data.todayViews = 0;
          data.todayClicks = 0;
          data.date = today;
        }
        return data;
      } catch {
        // Invalid data, use defaults
      }
    }
    return {
      totalViews: 0,
      totalClicks: 0,
      todayViews: 0,
      todayClicks: 0,
    };
  });

  // Save engagement to localStorage whenever it changes
  useEffect(() => {
    const data = {
      ...engagement,
      date: new Date().toDateString(),
    };
    localStorage.setItem(AD_ENGAGEMENT_KEY, JSON.stringify(data));
  }, [engagement]);

  const trackView = useCallback(async (adType: string, placement: string) => {
    // Update local state immediately for responsive UI
    setEngagement(prev => ({
      ...prev,
      totalViews: prev.totalViews + 1,
      todayViews: prev.todayViews + 1,
    }));

    // If authenticated, also track on the server for achievements
    if (isAuthenticated) {
      try {
        await api.trackAdEngagement({
          event_type: 'view',
          ad_type: adType,
          placement: placement,
        });
      } catch (error) {
        console.error('Failed to track ad view:', error);
      }
    }
  }, [isAuthenticated]);

  const trackClick = useCallback(async (adType: string, placement: string) => {
    // Update local state immediately
    setEngagement(prev => ({
      ...prev,
      totalClicks: prev.totalClicks + 1,
      todayClicks: prev.todayClicks + 1,
    }));

    // If authenticated, track on server for achievements
    if (isAuthenticated) {
      try {
        await api.trackAdEngagement({
          event_type: 'click',
          ad_type: adType,
          placement: placement,
        });
      } catch (error) {
        console.error('Failed to track ad click:', error);
      }
    }
  }, [isAuthenticated]);

  return (
    <AdContext.Provider
      value={{
        engagement,
        trackView,
        trackClick,
        isLoading,
        showPersonalizedAds,
        setShowPersonalizedAds,
      }}
    >
      {children}
    </AdContext.Provider>
  );
}

export function useAds() {
  const context = useContext(AdContext);
  if (context === undefined) {
    throw new Error('useAds must be used within an AdProvider');
  }
  return context;
}
