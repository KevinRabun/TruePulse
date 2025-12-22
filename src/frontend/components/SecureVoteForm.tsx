"use client";

import { useState, useEffect, useCallback } from "react";
import { TurnstileCaptcha, useTurnstile } from "./TurnstileCaptcha";
import {
  collectDeviceFingerprint,
  createSecureVoteRequest,
  BehavioralTracker,
  type SecureVoteRequest,
} from "@/lib/fraud-prevention";

interface SecureVoteFormProps {
  pollId: string;
  optionId: string;
  onVoteSuccess: (voteId: string) => void;
  onVoteError: (error: string) => void;
  disabled?: boolean;
  className?: string;
}

interface RiskAssessment {
  allowed: boolean;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  requires_captcha: boolean;
  blocked_reason?: string;
  risk_factors: string[];
}

interface VoteResponse {
  success: boolean;
  vote_id?: string;
  message?: string;
  error?: string;
  requires_captcha?: boolean;
  retry_after?: number;
}

/**
 * Secure voting form with fraud prevention
 * Integrates device fingerprinting, behavioral analysis, and CAPTCHA
 */
export function SecureVoteForm({
  pollId,
  optionId,
  onVoteSuccess,
  onVoteError,
  disabled = false,
  className = "",
}: SecureVoteFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCaptcha, setShowCaptcha] = useState(false);
  const [riskLevel, setRiskLevel] = useState<string | null>(null);
  const [riskFactors, setRiskFactors] = useState<string[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [behavioralTracker] = useState(() => new BehavioralTracker(pollId));

  const turnstile = useTurnstile();

  // Start behavioral tracking when component mounts
  useEffect(() => {
    behavioralTracker.startTracking();
    return () => behavioralTracker.stopTracking();
  }, [behavioralTracker]);

  // Pre-check risk when poll loads
  useEffect(() => {
    const checkRisk = async () => {
      try {
        const fingerprint = await collectDeviceFingerprint();
        const response = await fetch("/api/v1/secure-votes/pre-check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            poll_id: pollId,
            device_fingerprint: fingerprint,
          }),
          credentials: "include",
        });

        if (response.ok) {
          const assessment: RiskAssessment = await response.json();
          setRiskLevel(assessment.risk_level);
          setRiskFactors(assessment.risk_factors);

          if (assessment.requires_captcha) {
            setShowCaptcha(true);
          }

          if (!assessment.allowed) {
            onVoteError(
              assessment.blocked_reason || "Voting is not allowed at this time."
            );
          }
        }
      } catch (error) {
        console.error("Risk pre-check failed:", error);
        // Continue anyway - server will validate
      }
    };

    checkRisk();
  }, [pollId, onVoteError]);

  const submitVote = useCallback(async () => {
    if (isSubmitting || disabled) return;

    setIsSubmitting(true);
    setStatusMessage("Preparing secure vote...");

    try {
      // Collect all fraud prevention data
      const voteRequest: SecureVoteRequest = await createSecureVoteRequest(
        pollId,
        optionId,
        behavioralTracker,
        showCaptcha ? turnstile.token || undefined : undefined
      );

      setStatusMessage("Submitting vote...");

      const response = await fetch("/api/v1/secure-votes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(voteRequest),
        credentials: "include",
      });

      const result: VoteResponse = await response.json();

      if (response.ok && result.success && result.vote_id) {
        setStatusMessage("Vote recorded successfully!");
        onVoteSuccess(result.vote_id);
      } else if (result.requires_captcha) {
        // Server requested CAPTCHA verification
        setShowCaptcha(true);
        setStatusMessage(null);
        turnstile.reset();
      } else if (result.retry_after) {
        // Rate limited
        setStatusMessage(
          `Please wait ${result.retry_after} seconds before voting again.`
        );
        setTimeout(() => setStatusMessage(null), result.retry_after * 1000);
      } else {
        onVoteError(result.error || result.message || "Vote failed");
        setStatusMessage(null);
      }
    } catch (error) {
      console.error("Vote submission error:", error);
      onVoteError("Network error. Please try again.");
      setStatusMessage(null);
    } finally {
      setIsSubmitting(false);
    }
  }, [
    isSubmitting,
    disabled,
    pollId,
    optionId,
    behavioralTracker,
    showCaptcha,
    turnstile,
    onVoteSuccess,
    onVoteError,
  ]);

  const handleCaptchaVerify = useCallback(
    (token: string) => {
      turnstile.handleVerify(token);
      // Auto-submit after CAPTCHA if user was trying to vote
      if (isSubmitting) {
        setTimeout(submitVote, 100);
      }
    },
    [turnstile, isSubmitting, submitVote]
  );

  const canVote =
    !disabled &&
    !isSubmitting &&
    (!showCaptcha || turnstile.isVerified) &&
    riskLevel !== "critical";

  return (
    <div className={`secure-vote-form ${className}`}>
      {/* Risk indicator (only shown in development or for high risk) */}
      {riskLevel && (riskLevel === "high" || riskLevel === "critical") && (
        <div
          className={`text-xs px-2 py-1 rounded mb-2 ${
            riskLevel === "high"
              ? "bg-amber-100 text-amber-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {riskLevel === "critical"
            ? "Additional verification required"
            : "Enhanced security active"}
        </div>
      )}

      {/* Risk factors (for transparency) */}
      {riskFactors.length > 0 && process.env.NODE_ENV === "development" && (
        <div className="text-xs text-gray-500 mb-2">
          Risk factors: {riskFactors.join(", ")}
        </div>
      )}

      {/* CAPTCHA challenge */}
      {showCaptcha && (
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-2">
            Please complete this security check to continue:
          </p>
          <TurnstileCaptcha
            onVerify={handleCaptchaVerify}
            onExpire={turnstile.handleExpire}
            onError={turnstile.handleError}
            theme="auto"
            size="normal"
          />
        </div>
      )}

      {/* Status message */}
      {statusMessage && (
        <div className="text-sm text-blue-600 mb-2 animate-pulse">
          {statusMessage}
        </div>
      )}

      {/* Vote button */}
      <button
        onClick={submitVote}
        disabled={!canVote}
        className={`w-full py-2 px-4 rounded-lg font-medium transition-all ${
          canVote
            ? "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800"
            : "bg-gray-300 text-gray-500 cursor-not-allowed"
        }`}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-4 w-4"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
                fill="none"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Submitting...
          </span>
        ) : showCaptcha && !turnstile.isVerified ? (
          "Complete verification to vote"
        ) : (
          "Vote"
        )}
      </button>

      {/* Security notice */}
      <p className="text-xs text-gray-400 mt-2 text-center">
        🔒 Your vote is protected by multi-layer security
      </p>
    </div>
  );
}

/**
 * Invisible secure vote trigger
 * Collects fraud prevention data without visible CAPTCHA
 */
export function useSecureVote(pollId: string) {
  const [tracker] = useState(() => new BehavioralTracker(pollId));
  // Start tracking immediately and set ready state synchronously
  const [isReady] = useState(() => {
    // Tracker starts tracking on instantiation via the state initializer above
    return true;
  });
  const [riskAssessment, setRiskAssessment] = useState<RiskAssessment | null>(
    null
  );

  useEffect(() => {
    tracker.startTracking();
    return () => tracker.stopTracking();
  }, [tracker]);

  const preCheck = useCallback(async () => {
    const fingerprint = await collectDeviceFingerprint();
    const response = await fetch("/api/v1/secure-votes/pre-check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        poll_id: pollId,
        device_fingerprint: fingerprint,
      }),
      credentials: "include",
    });

    if (response.ok) {
      const assessment = await response.json();
      setRiskAssessment(assessment);
      return assessment;
    }
    return null;
  }, [pollId]);

  const submitVote = useCallback(
    async (optionId: string, captchaToken?: string) => {
      const voteRequest = await createSecureVoteRequest(
        pollId,
        optionId,
        tracker,
        captchaToken
      );

      const response = await fetch("/api/v1/secure-votes/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(voteRequest),
        credentials: "include",
      });

      return response.json();
    },
    [pollId, tracker]
  );

  return {
    isReady,
    riskAssessment,
    preCheck,
    submitVote,
    tracker,
  };
}

export default SecureVoteForm;
