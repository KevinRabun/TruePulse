"use client";

import { useEffect, useRef, useCallback, useState } from "react";

interface TurnstileInstance {
  render: (
    container: string | HTMLElement,
    options: TurnstileOptions
  ) => string;
  reset: (widgetId: string) => void;
  remove: (widgetId: string) => void;
  getResponse: (widgetId: string) => string | undefined;
  isExpired: (widgetId: string) => boolean;
}

interface TurnstileOptions {
  sitekey: string;
  callback?: (token: string) => void;
  "expired-callback"?: () => void;
  "error-callback"?: (error: Error) => void;
  theme?: "light" | "dark" | "auto";
  size?: "normal" | "compact" | "invisible";
  tabindex?: number;
  action?: string;
  cData?: string;
  appearance?: "always" | "execute" | "interaction-only";
  retry?: "auto" | "never";
  "retry-interval"?: number;
  "refresh-expired"?: "auto" | "manual" | "never";
  language?: string;
}

declare global {
  interface Window {
    turnstile?: TurnstileInstance;
    onTurnstileLoad?: () => void;
  }
}

interface TurnstileCaptchaProps {
  siteKey?: string;
  onVerify: (token: string) => void;
  onExpire?: () => void;
  onError?: (error: Error) => void;
  theme?: "light" | "dark" | "auto";
  size?: "normal" | "compact" | "invisible";
  action?: string;
  className?: string;
  appearance?: "always" | "execute" | "interaction-only";
}

/**
 * Cloudflare Turnstile CAPTCHA component
 * Privacy-friendly alternative to reCAPTCHA
 */
export function TurnstileCaptcha({
  siteKey = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY,
  onVerify,
  onExpire,
  onError,
  theme = "auto",
  size = "normal",
  action,
  className = "",
  appearance = "always",
}: TurnstileCaptchaProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = useCallback(
    (token: string) => {
      onVerify(token);
    },
    [onVerify]
  );

  const handleExpire = useCallback(() => {
    if (onExpire) {
      onExpire();
    }
  }, [onExpire]);

  const handleError = useCallback(
    (err: Error) => {
      setError("CAPTCHA verification failed. Please try again.");
      if (onError) {
        onError(err);
      }
    },
    [onError]
  );

  // Load Turnstile script
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Check if script is already loaded
    if (window.turnstile) {
      setIsLoaded(true);
      return;
    }

    // Check if script is already being loaded
    const existingScript = document.querySelector(
      'script[src*="challenges.cloudflare.com"]'
    );
    if (existingScript) {
      existingScript.addEventListener("load", () => setIsLoaded(true));
      return;
    }

    // Load script
    const script = document.createElement("script");
    script.src =
      "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit&onload=onTurnstileLoad";
    script.async = true;
    script.defer = true;

    window.onTurnstileLoad = () => {
      setIsLoaded(true);
    };

    script.onerror = () => {
      setError("Failed to load CAPTCHA. Please refresh the page.");
    };

    document.head.appendChild(script);

    return () => {
      // Cleanup callback
      delete window.onTurnstileLoad;
    };
  }, []);

  // Render widget when script is loaded
  useEffect(() => {
    if (!isLoaded || !window.turnstile || !containerRef.current || !siteKey)
      return;

    // Remove existing widget if any
    if (widgetIdRef.current) {
      try {
        window.turnstile.remove(widgetIdRef.current);
      } catch {
        // Widget might not exist
      }
    }

    // Render new widget
    try {
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: handleVerify,
        "expired-callback": handleExpire,
        "error-callback": handleError,
        theme,
        size,
        action,
        appearance,
        retry: "auto",
        "retry-interval": 5000,
        "refresh-expired": "auto",
      });
    } catch (err) {
      setError("Failed to initialize CAPTCHA.");
      console.error("Turnstile render error:", err);
    }

    return () => {
      // Cleanup widget on unmount
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          // Widget might not exist
        }
        widgetIdRef.current = null;
      }
    };
  }, [
    isLoaded,
    siteKey,
    handleVerify,
    handleExpire,
    handleError,
    theme,
    size,
    action,
    appearance,
  ]);

  // Reset function exposed via ref
  const reset = useCallback(() => {
    if (widgetIdRef.current && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
      setError(null);
    }
  }, []);

  // Get current token
  const getToken = useCallback(() => {
    if (widgetIdRef.current && window.turnstile) {
      return window.turnstile.getResponse(widgetIdRef.current);
    }
    return undefined;
  }, []);

  // Check if expired
  const isExpired = useCallback(() => {
    if (widgetIdRef.current && window.turnstile) {
      return window.turnstile.isExpired(widgetIdRef.current);
    }
    return false;
  }, []);

  if (!siteKey) {
    return (
      <div className="text-sm text-amber-600 p-2 bg-amber-50 rounded">
        CAPTCHA not configured. Contact support if this persists.
      </div>
    );
  }

  return (
    <div className={className}>
      {error && (
        <div className="text-sm text-red-600 mb-2 p-2 bg-red-50 rounded">
          {error}
          <button
            onClick={reset}
            className="ml-2 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}
      <div
        ref={containerRef}
        className="cf-turnstile"
        data-sitekey={siteKey}
      />
      {!isLoaded && (
        <div className="animate-pulse bg-gray-200 rounded h-16 w-[300px]" />
      )}
    </div>
  );
}

/**
 * Hook for programmatic Turnstile control
 */
export function useTurnstile() {
  const [token, setToken] = useState<string | null>(null);
  const [isVerified, setIsVerified] = useState(false);
  const [isExpired, setIsExpired] = useState(false);

  const handleVerify = useCallback((newToken: string) => {
    setToken(newToken);
    setIsVerified(true);
    setIsExpired(false);
  }, []);

  const handleExpire = useCallback(() => {
    setToken(null);
    setIsVerified(false);
    setIsExpired(true);
  }, []);

  const handleError = useCallback(() => {
    setToken(null);
    setIsVerified(false);
  }, []);

  const reset = useCallback(() => {
    setToken(null);
    setIsVerified(false);
    setIsExpired(false);
  }, []);

  return {
    token,
    isVerified,
    isExpired,
    handleVerify,
    handleExpire,
    handleError,
    reset,
  };
}

export default TurnstileCaptcha;
