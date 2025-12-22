"use client";

/**
 * Passkey Management Component
 *
 * Displays and manages user's registered passkeys.
 * Allows adding new passkeys and removing existing ones.
 */

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Fingerprint,
  Loader2,
  AlertCircle,
  Trash2,
  Plus,
  Key,
  Clock,
  Shield,
  Cloud,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { getPasskeys, deletePasskey, isPasskeySupported } from "@/lib/passkey";
import { useAuthStore } from "@/lib/store";
import { PasskeyRegister } from "./PasskeyRegister";

interface PasskeyInfo {
  id: string;
  deviceName: string;
  createdAt: string;
  lastUsedAt: string | null;
  backupEligible: boolean;
  backupState: boolean;
}

interface PasskeyManagementProps {
  className?: string;
}

export function PasskeyManagement({ className = "" }: PasskeyManagementProps) {
  const [passkeys, setPasskeys] = useState<PasskeyInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const [showRegister, setShowRegister] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const { accessToken, user } = useAuthStore();

  const loadPasskeys = useCallback(async () => {
    if (!accessToken) return;

    setIsLoading(true);
    setError(null);

    const result = await getPasskeys(accessToken);

    if (result.success && result.passkeys) {
      setPasskeys(result.passkeys);
    } else {
      setError(result.error || "Failed to load passkeys");
    }

    setIsLoading(false);
  }, [accessToken]);

  useEffect(() => {
    setIsSupported(isPasskeySupported());
    loadPasskeys();
  }, [loadPasskeys]);

  const handleDelete = async (passkeyId: string, deviceName: string) => {
    if (!accessToken) return;

    // Confirm deletion
    if (
      !confirm(
        `Are you sure you want to remove the passkey "${deviceName}"? You'll need to use another method to sign in.`
      )
    ) {
      return;
    }

    setDeletingId(passkeyId);
    setDeleteError(null);

    const result = await deletePasskey(accessToken, passkeyId);

    if (result.success) {
      setPasskeys((prev) => prev.filter((p) => p.id !== passkeyId));
    } else {
      setDeleteError(result.error || "Failed to delete passkey");
    }

    setDeletingId(null);
  };

  const handleRegisterSuccess = () => {
    setShowRegister(false);
    loadPasskeys();
  };

  // Not supported message
  if (isSupported === false) {
    return (
      <div className={`p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg ${className}`}>
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Your browser doesn&apos;t support passkeys. Please use a modern browser to
            manage passkey authentication.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-100 dark:bg-indigo-900 rounded-lg">
            <Key className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Passkeys
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Secure passwordless sign-in
            </p>
          </div>
        </div>

        {!showRegister && passkeys.length > 0 && (
          <button
            onClick={() => setShowRegister(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Passkey
          </button>
        )}
      </div>

      {/* Passkey-only mode indicator */}
      {user?.passkeyOnly && (
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <Shield className="h-5 w-5 text-green-600 dark:text-green-400" />
          <p className="text-sm text-green-800 dark:text-green-200">
            <strong>Passkey-only mode:</strong> Your account uses passkeys exclusively
            for enhanced security.
          </p>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Delete error */}
      {deleteError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg"
        >
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 dark:text-red-300">{deleteError}</p>
        </motion.div>
      )}

      {/* Registration form */}
      <AnimatePresence>
        {showRegister && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="border border-gray-200 dark:border-gray-700 rounded-xl p-5 overflow-hidden"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-medium text-gray-900 dark:text-white">
                Add a new passkey
              </h3>
              <button
                onClick={() => setShowRegister(false)}
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                Cancel
              </button>
            </div>
            <PasskeyRegister
              onSuccess={handleRegisterSuccess}
              onError={(error) => setDeleteError(error)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Passkeys list */}
      {!isLoading && passkeys.length > 0 && (
        <div className="space-y-3">
          {passkeys.map((passkey) => (
            <motion.div
              key={passkey.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700"
            >
              <div className="flex items-center gap-4">
                <div className="p-2 bg-indigo-100 dark:bg-indigo-900/50 rounded-lg">
                  <Fingerprint className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-medium text-gray-900 dark:text-white">
                      {passkey.deviceName}
                    </p>
                    {passkey.backupState && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs rounded-full">
                        <Cloud className="h-3 w-3" />
                        Synced
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-sm text-gray-500 dark:text-gray-400">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Created{" "}
                      {formatDistanceToNow(new Date(passkey.createdAt), {
                        addSuffix: true,
                      })}
                    </span>
                    {passkey.lastUsedAt && (
                      <span>
                        Last used{" "}
                        {formatDistanceToNow(new Date(passkey.lastUsedAt), {
                          addSuffix: true,
                        })}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <button
                onClick={() => handleDelete(passkey.id, passkey.deviceName)}
                disabled={deletingId === passkey.id}
                className="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors disabled:opacity-50"
                title="Remove passkey"
              >
                {deletingId === passkey.id ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Trash2 className="h-5 w-5" />
                )}
              </button>
            </motion.div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && passkeys.length === 0 && !showRegister && (
        <div className="text-center py-8">
          <div className="mx-auto w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
            <Fingerprint className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No passkeys yet
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4 max-w-sm mx-auto">
            Add a passkey to sign in securely using Face ID, Touch ID, or Windows
            Hello.
          </p>
          <button
            onClick={() => setShowRegister(true)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg font-medium hover:from-indigo-700 hover:to-purple-700 transition-all"
          >
            <Plus className="h-5 w-5" />
            Add Your First Passkey
          </button>
        </div>
      )}
    </div>
  );
}
