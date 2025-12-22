"use client";

/**
 * Passkey Login Button Component
 *
 * Provides a one-click passkey authentication experience.
 * Falls back gracefully if passkeys are not supported.
 */

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Fingerprint, Loader2, AlertCircle, CheckCircle } from "lucide-react";
import {
  isPasskeySupported,
  hasPlatformAuthenticator,
  authenticateWithPasskey,
} from "@/lib/passkey";
import { useAuthStore } from "@/lib/store";

interface PasskeyLoginButtonProps {
  email?: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
  className?: string;
  variant?: "primary" | "secondary";
}

export function PasskeyLoginButton({
  email,
  onSuccess,
  onError,
  className = "",
  variant = "primary",
}: PasskeyLoginButtonProps) {
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [hasPlatform, setHasPlatform] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { setAccessToken, setRefreshToken, setUser } = useAuthStore();

  // Check for passkey support on mount
  useEffect(() => {
    const checkSupport = async () => {
      const supported = isPasskeySupported();
      setIsSupported(supported);

      if (supported) {
        const platform = await hasPlatformAuthenticator();
        setHasPlatform(platform);
      }
    };
    checkSupport();
  }, []);

  const handlePasskeyLogin = async () => {
    if (!isSupported) return;

    setIsLoading(true);
    setStatus("idle");
    setErrorMessage(null);

    try {
      const result = await authenticateWithPasskey(email);

      if (result.success && result.accessToken && result.user) {
        // Store tokens and user info
        setAccessToken(result.accessToken);
        if (result.refreshToken) {
          setRefreshToken(result.refreshToken);
        }
        setUser(result.user);

        setStatus("success");
        onSuccess?.();
      } else {
        setStatus("error");
        setErrorMessage(result.error || "Authentication failed");
        onError?.(result.error || "Authentication failed");
      }
    } catch (error) {
      setStatus("error");
      const message = error instanceof Error ? error.message : "An unexpected error occurred";
      setErrorMessage(message);
      onError?.(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Don't render if checking support or not supported
  if (isSupported === null) {
    return (
      <div className={`flex items-center justify-center py-3 ${className}`}>
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!isSupported) {
    return null; // Silently hide if not supported
  }

  const baseClasses =
    "w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed";

  const variantClasses =
    variant === "primary"
      ? "bg-linear-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-700 hover:to-purple-700 shadow-lg hover:shadow-xl"
      : "bg-white dark:bg-gray-800 border-2 border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 hover:border-indigo-400 dark:hover:border-indigo-600";

  return (
    <div className="space-y-2">
      <motion.button
        type="button"
        onClick={handlePasskeyLogin}
        disabled={isLoading || status === "success"}
        className={`${baseClasses} ${variantClasses} ${className}`}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {isLoading ? (
          <>
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Verifying...</span>
          </>
        ) : status === "success" ? (
          <>
            <CheckCircle className="h-5 w-5" />
            <span>Signed in!</span>
          </>
        ) : (
          <>
            <Fingerprint className="h-5 w-5" />
            <span>
              {hasPlatform
                ? "Sign in with Face ID / Touch ID"
                : "Sign in with Passkey"}
            </span>
          </>
        )}
      </motion.button>

      {status === "error" && errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400"
        >
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </motion.div>
      )}
    </div>
  );
}

/**
 * Passkey promotion banner for users without passkeys
 */
interface PasskeyPromoBannerProps {
  onSetup?: () => void;
  onDismiss?: () => void;
}

export function PasskeyPromoBanner({ onSetup, onDismiss }: PasskeyPromoBannerProps) {
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    setIsSupported(isPasskeySupported());
    // Check if user has dismissed the banner before
    const dismissed = localStorage.getItem("passkey-promo-dismissed");
    if (dismissed) setDismissed(true);
  }, []);

  if (!isSupported || dismissed) return null;

  const handleDismiss = () => {
    localStorage.setItem("passkey-promo-dismissed", "true");
    setDismissed(true);
    onDismiss?.();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-linear-to-r from-indigo-500 to-purple-600 rounded-lg p-4 text-white shadow-lg"
    >
      <div className="flex items-start gap-3">
        <div className="shrink-0 p-2 bg-white/20 rounded-full">
          <Fingerprint className="h-6 w-6" />
        </div>
        <div className="flex-1">
          <h3 className="font-semibold">Upgrade to Passkey Login</h3>
          <p className="text-sm text-white/90 mt-1">
            Use Face ID, Touch ID, or Windows Hello for faster, more secure sign-ins.
            No passwords to remember!
          </p>
          <div className="flex gap-2 mt-3">
            <button
              onClick={onSetup}
              className="px-4 py-1.5 bg-white text-indigo-700 rounded-md text-sm font-medium hover:bg-white/90 transition-colors"
            >
              Set up now
            </button>
            <button
              onClick={handleDismiss}
              className="px-4 py-1.5 text-white/80 hover:text-white text-sm transition-colors"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
