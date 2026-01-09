"use client";

/**
 * Passkey Registration Component
 *
 * Allows users to register new passkeys for their account.
 * Requires phone verification before passkey registration.
 */

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Fingerprint,
  Loader2,
  AlertCircle,
  CheckCircle,
  Shield,
} from "lucide-react";
import {
  isPasskeySupported,
  hasPlatformAuthenticator,
  registerPasskey,
  getPasskeyBrowserWarning,
} from "@/lib/passkey";
import { useAuthStore } from "@/lib/store";

interface PasskeyRegisterProps {
  onSuccess?: (passkey: { id: string; deviceName: string }) => void;
  onError?: (error: string) => void;
  className?: string;
}

export function PasskeyRegister({
  onSuccess,
  onError,
  className = "",
}: PasskeyRegisterProps) {
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [hasPlatform, setHasPlatform] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [deviceName, setDeviceName] = useState("");
  const [browserWarning, setBrowserWarning] = useState<{ message: string; browserName: string } | null>(null);

  const { accessToken } = useAuthStore();

  // Check for passkey support on mount
  useEffect(() => {
    const checkSupport = async () => {
      const supported = isPasskeySupported();
      setIsSupported(supported);

      if (supported) {
        const platform = await hasPlatformAuthenticator();
        setHasPlatform(platform);
      }
      
      // Check for iOS browser limitations
      const warning = getPasskeyBrowserWarning();
      setBrowserWarning(warning);
    };
    checkSupport();
  }, []);

  const handleRegister = async () => {
    if (!isSupported || !accessToken) return;

    setIsLoading(true);
    setStatus("idle");
    setErrorMessage(null);

    try {
      const result = await registerPasskey(
        accessToken,
        deviceName || undefined
      );

      if (result.success && result.passkey) {
        setStatus("success");
        onSuccess?.(result.passkey);
      } else {
        setStatus("error");
        setErrorMessage(result.error || "Registration failed");
        onError?.(result.error || "Registration failed");
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

  // Don't render if not supported
  if (isSupported === false) {
    return (
      <div className={`p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg ${className}`}>
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-800 dark:text-amber-200">
              Your browser doesn&apos;t support passkeys. Please use a modern browser
              like Chrome, Safari, or Edge to set up passkey authentication.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Loading state
  if (isSupported === null) {
    return (
      <div className={`flex items-center justify-center py-8 ${className}`}>
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* iOS Safari-only warning */}
      {browserWarning && (
        <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800/50">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                Safari Required on iOS
              </p>
              <p className="text-sm text-amber-700 dark:text-amber-300">
                {browserWarning.message}
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
                This is an Apple platform limitation that affects all third-party browsers on iOS.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Benefits section */}
      <div className="bg-linear-to-br from-indigo-50 to-purple-50 dark:from-indigo-900/20 dark:to-purple-900/20 rounded-xl p-5">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-800 rounded-lg">
            <Shield className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              Why use a passkey?
            </h3>
          </div>
        </div>
        <ul className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            <span>
              <strong>Phishing-proof:</strong> Passkeys can&apos;t be stolen by fake websites
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            <span>
              <strong>No passwords:</strong> Sign in with Face ID, Touch ID, or Windows Hello
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            <span>
              <strong>Synced:</strong> Works across your devices via iCloud, Google, or Microsoft
            </span>
          </li>
        </ul>
      </div>

      {/* Device name input */}
      <div>
        <label
          htmlFor="device-name"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
        >
          Device name (optional)
        </label>
        <input
          id="device-name"
          type="text"
          value={deviceName}
          onChange={(e) => setDeviceName(e.target.value)}
          placeholder="e.g., MacBook Pro, iPhone 15"
          className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        />
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          This helps you identify the passkey later
        </p>
      </div>

      {/* Register button */}
      <AnimatePresence mode="wait">
        {status === "success" ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg"
          >
            <CheckCircle className="h-6 w-6 text-green-600 dark:text-green-400" />
            <div>
              <p className="font-medium text-green-800 dark:text-green-200">
                Passkey registered!
              </p>
              <p className="text-sm text-green-700 dark:text-green-300">
                You can now sign in using your passkey.
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.button
            key="register-button"
            type="button"
            onClick={handleRegister}
            disabled={isLoading}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-linear-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-700 hover:to-purple-700 shadow-lg hover:shadow-xl transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Creating passkey...</span>
              </>
            ) : (
              <>
                <Fingerprint className="h-5 w-5" />
                <span>
                  {hasPlatform
                    ? "Create Passkey with Face ID / Touch ID"
                    : "Create Passkey"}
                </span>
              </>
            )}
          </motion.button>
        )}
      </AnimatePresence>

      {/* Error message */}
      {status === "error" && errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
        >
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{errorMessage}</p>
        </motion.div>
      )}
    </div>
  );
}
