'use client';

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';

const COOKIE_CONSENT_KEY = 'truepulse_cookie_consent';
const COOKIE_CONSENT_VERSION = '1.0';

interface CookieConsentState {
  essential: boolean;
  analytics: boolean;
  advertising: boolean;
  version: string;
  timestamp: string;
}

/**
 * Cookie Consent Banner Component
 * 
 * GDPR and ePrivacy Directive Compliance:
 * - Essential cookies: Always enabled (session management, security)
 * - Analytics cookies: Optional, for understanding usage patterns
 * - Advertising cookies: Optional, for Google Ads integration
 * 
 * Users can modify their preferences at any time via the privacy settings.
 */
export default function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [preferences, setPreferences] = useState<CookieConsentState>({
    essential: true, // Always required
    analytics: false,
    advertising: false,
    version: COOKIE_CONSENT_VERSION,
    timestamp: '',
  });

  useEffect(() => {
    // Check if user has already consented
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as CookieConsentState;
        // Check if consent version matches current version
        if (parsed.version === COOKIE_CONSENT_VERSION) {
          setPreferences(parsed);
          return; // Don't show banner if already consented
        }
      } catch {
        // Invalid stored consent, show banner
      }
    }
    // Small delay to prevent flash during hydration
    const timer = setTimeout(() => setShowBanner(true), 500);
    return () => clearTimeout(timer);
  }, []);

  const saveConsent = (newPreferences: Partial<CookieConsentState>) => {
    const updated: CookieConsentState = {
      ...preferences,
      ...newPreferences,
      version: COOKIE_CONSENT_VERSION,
      timestamp: new Date().toISOString(),
    };
    localStorage.setItem(COOKIE_CONSENT_KEY, JSON.stringify(updated));
    setPreferences(updated);
    setShowBanner(false);

    // Trigger consent event for analytics/ads integration
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('cookieConsentUpdated', { detail: updated })
      );
    }
  };

  const acceptAll = () => {
    saveConsent({
      essential: true,
      analytics: true,
      advertising: true,
    });
  };

  const acceptEssentialOnly = () => {
    saveConsent({
      essential: true,
      analytics: false,
      advertising: false,
    });
  };

  const saveCustomPreferences = () => {
    saveConsent(preferences);
  };

  if (!showBanner) {
    return null;
  }

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 shadow-lg"
      role="dialog"
      aria-labelledby="cookie-consent-title"
      aria-describedby="cookie-consent-description"
    >
      <div className="max-w-6xl mx-auto">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2
              id="cookie-consent-title"
              className="text-lg font-semibold text-gray-900 dark:text-white mb-2"
            >
              🍪 Cookie Preferences
            </h2>
            <p
              id="cookie-consent-description"
              className="text-sm text-gray-600 dark:text-gray-400 mb-4"
            >
              We use cookies to enhance your experience, analyze site traffic, and serve
              personalized ads. You can customize your preferences or accept all cookies.
              Essential cookies are always enabled for security and core functionality.
              See our{' '}
              <a
                href="/privacy"
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                Privacy Policy
              </a>{' '}
              for more details.
            </p>

            {showDetails && (
              <div className="space-y-3 mb-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                {/* Essential Cookies */}
                <div className="flex items-center justify-between">
                  <div>
                    <label className="font-medium text-gray-900 dark:text-white">
                      Essential Cookies
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Required for authentication, security, and core functionality.
                      Cannot be disabled.
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={true}
                    disabled
                    className="w-5 h-5 rounded border-gray-300 text-blue-600 cursor-not-allowed opacity-60"
                    aria-label="Essential cookies (always enabled)"
                  />
                </div>

                {/* Analytics Cookies */}
                <div className="flex items-center justify-between">
                  <div>
                    <label
                      htmlFor="analytics-cookies"
                      className="font-medium text-gray-900 dark:text-white cursor-pointer"
                    >
                      Analytics Cookies
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Help us understand how visitors interact with our site to improve
                      user experience.
                    </p>
                  </div>
                  <input
                    id="analytics-cookies"
                    type="checkbox"
                    checked={preferences.analytics}
                    onChange={(e) =>
                      setPreferences({ ...preferences, analytics: e.target.checked })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </div>

                {/* Advertising Cookies */}
                <div className="flex items-center justify-between">
                  <div>
                    <label
                      htmlFor="advertising-cookies"
                      className="font-medium text-gray-900 dark:text-white cursor-pointer"
                    >
                      Advertising Cookies
                    </label>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Used to show personalized ads based on your interests. We partner
                      with Google Ads.
                    </p>
                  </div>
                  <input
                    id="advertising-cookies"
                    type="checkbox"
                    checked={preferences.advertising}
                    onChange={(e) =>
                      setPreferences({ ...preferences, advertising: e.target.checked })
                    }
                    className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                  />
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                onClick={acceptAll}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
              >
                Accept All
              </button>
              <button
                onClick={acceptEssentialOnly}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors font-medium text-sm"
              >
                Essential Only
              </button>
              {showDetails ? (
                <button
                  onClick={saveCustomPreferences}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium text-sm"
                >
                  Save Preferences
                </button>
              ) : (
                <button
                  onClick={() => setShowDetails(true)}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors font-medium text-sm underline"
                >
                  Customize
                </button>
              )}
            </div>
          </div>

          <button
            onClick={acceptEssentialOnly}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-1"
            aria-label="Close cookie banner (accepts essential only)"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to check cookie consent status
 * Use this in components that need to conditionally load analytics/ads
 */
export function useCookieConsent() {
  const [consent, setConsent] = useState<CookieConsentState | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(COOKIE_CONSENT_KEY);
    if (stored) {
      try {
        setConsent(JSON.parse(stored));
      } catch {
        setConsent(null);
      }
    }

    // Listen for consent updates
    const handleUpdate = (e: CustomEvent<CookieConsentState>) => {
      setConsent(e.detail);
    };

    window.addEventListener(
      'cookieConsentUpdated',
      handleUpdate as EventListener
    );
    return () =>
      window.removeEventListener(
        'cookieConsentUpdated',
        handleUpdate as EventListener
      );
  }, []);

  return consent;
}
