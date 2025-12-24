/**
 * Passkey (WebAuthn/FIDO2) authentication client library.
 *
 * Provides functions for registering and authenticating with passkeys.
 * Uses the @simplewebauthn/browser library for WebAuthn operations.
 */

import {
  startAuthentication,
  startRegistration,
  browserSupportsWebAuthn,
  platformAuthenticatorIsAvailable,
} from "@simplewebauthn/browser";
import type {
  AuthenticationResponseJSON,
  RegistrationResponseJSON,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
} from "@simplewebauthn/browser";
import { collectDeviceFingerprint } from "./fraud-prevention";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/**
 * Device information for trust scoring
 */
interface DeviceInfo {
  fingerprint: string | null;
  platform: string;
  browser: string;
  screenResolution: string;
  timezone: string;
}

/**
 * Result of passkey registration
 */
interface RegisterPasskeyResult {
  success: boolean;
  passkey?: {
    id: string;
    deviceName: string;
    createdAt: string;
  };
  error?: string;
}

/**
 * Result of passkey authentication
 */
interface AuthenticateResult {
  success: boolean;
  accessToken?: string;
  refreshToken?: string;
  tokenType?: string;
  user?: {
    id: string;
    email: string;
    username: string;
    display_name?: string;
    isVerified: boolean;
    phoneVerified: boolean;
    emailVerified: boolean;
    hasPasskey: boolean;
    passkeyOnly: boolean;
  };
  error?: string;
}

/**
 * Information about a registered passkey
 */
interface PasskeyInfo {
  id: string;
  deviceName: string;
  createdAt: string;
  lastUsedAt: string | null;
  backupEligible: boolean;
  backupState: boolean;
}

/**
 * Check if WebAuthn/Passkeys are supported by the browser
 */
export function isPasskeySupported(): boolean {
  return browserSupportsWebAuthn();
}

/**
 * Check if the device has a platform authenticator (Face ID, Touch ID, Windows Hello)
 */
export async function hasPlatformAuthenticator(): Promise<boolean> {
  return platformAuthenticatorIsAvailable();
}

/**
 * Get current device information for trust scoring
 */
async function getDeviceInfo(): Promise<DeviceInfo> {
  let fingerprint: string | null = null;
  try {
    const fpResult = await collectDeviceFingerprint();
    // Create a fingerprint hash from the collected data
    fingerprint = fpResult.canvas_hash || fpResult.audio_hash || null;
  } catch (e) {
    console.warn("Failed to get device fingerprint:", e);
  }

  return {
    fingerprint,
    platform: navigator.platform || "unknown",
    browser: navigator.userAgent.split(" ").pop() || "unknown",
    screenResolution: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
}

/**
 * Get registration options from the server and start WebAuthn registration
 */
export async function registerPasskey(
  accessToken: string,
  deviceName?: string
): Promise<RegisterPasskeyResult> {
  if (!isPasskeySupported()) {
    return {
      success: false,
      error: "Your browser does not support passkeys. Please use a modern browser.",
    };
  }

  try {
    const deviceInfo = await getDeviceInfo();

    // Step 1: Get registration options from server
    const optionsResponse = await fetch(`${API_BASE}/passkeys/register/options`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ device_info: deviceInfo }),
    });

    if (!optionsResponse.ok) {
      const error = await optionsResponse.json();
      return {
        success: false,
        error: error.detail || "Failed to get registration options",
      };
    }

    const options = await optionsResponse.json();
    const challengeId = options.challengeId;

    // Convert server options to WebAuthn format
    const webAuthnOptions: PublicKeyCredentialCreationOptionsJSON = {
      rp: options.rp,
      user: options.user,
      challenge: options.challenge,
      pubKeyCredParams: options.pubKeyCredParams,
      timeout: options.timeout,
      attestation: options.attestation,
      excludeCredentials: options.excludeCredentials,
      authenticatorSelection: options.authenticatorSelection,
    };

    // Step 2: Start WebAuthn registration (prompts user for biometric)
    let credential: RegistrationResponseJSON;
    try {
      credential = await startRegistration({ optionsJSON: webAuthnOptions });
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === "NotAllowedError") {
          return {
            success: false,
            error: "Registration was cancelled or timed out. Please try again.",
          };
        }
        if (e.name === "InvalidStateError") {
          return {
            success: false,
            error: "A passkey already exists for this device.",
          };
        }
      }
      throw e;
    }

    // Step 3: Send credential to server for verification
    // Send credential as an object (not stringified) - matches SimpleWebAuthn examples
    // The backend accepts it as a dict and passes directly to parse_registration_credential_json
    const verifyResponse = await fetch(`${API_BASE}/passkeys/register/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        challengeId,
        credential,  // Object, not JSON.stringify(credential) - avoids double-stringify
        deviceName: deviceName || `${deviceInfo.platform} - ${new Date().toLocaleDateString()}`,
      }),
    });

    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      // Handle both string detail and Pydantic validation error array format
      let errorMessage = "Failed to verify registration";
      if (typeof error.detail === "string") {
        errorMessage = error.detail;
      } else if (Array.isArray(error.detail) && error.detail.length > 0) {
        // Pydantic validation error format: [{type, loc, msg, input}, ...]
        errorMessage = error.detail.map((e: { msg: string; loc: string[] }) => 
          `${e.loc?.join(".")}: ${e.msg}`
        ).join("; ");
      }
      return {
        success: false,
        error: errorMessage,
      };
    }

    const result = await verifyResponse.json();
    return {
      success: true,
      passkey: result.passkey,
    };
  } catch (e) {
    console.error("Passkey registration error:", e);
    return {
      success: false,
      error: e instanceof Error ? e.message : "An unexpected error occurred",
    };
  }
}

/**
 * Authenticate with a passkey
 *
 * @param email - Optional email for non-discoverable credential flow.
 *                If not provided, uses discoverable credential flow.
 */
export async function authenticateWithPasskey(
  email?: string
): Promise<AuthenticateResult> {
  if (!isPasskeySupported()) {
    return {
      success: false,
      error: "Your browser does not support passkeys. Please use a modern browser.",
    };
  }

  try {
    const deviceInfo = await getDeviceInfo();

    // Step 1: Get authentication options from server
    const optionsResponse = await fetch(`${API_BASE}/passkeys/authenticate/options`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        device_info: deviceInfo,
      }),
    });

    if (!optionsResponse.ok) {
      const error = await optionsResponse.json();
      return {
        success: false,
        error: error.detail || "Failed to get authentication options",
      };
    }

    const options = await optionsResponse.json();
    const challengeId = options.challengeId;

    // Convert server options to WebAuthn format
    const webAuthnOptions: PublicKeyCredentialRequestOptionsJSON = {
      rpId: options.rpId,
      challenge: options.challenge,
      timeout: options.timeout,
      userVerification: options.userVerification,
      allowCredentials: options.allowCredentials,
    };

    // Step 2: Start WebAuthn authentication (prompts user for biometric)
    let credential: AuthenticationResponseJSON;
    try {
      credential = await startAuthentication({ optionsJSON: webAuthnOptions });
    } catch (e) {
      if (e instanceof Error) {
        if (e.name === "NotAllowedError") {
          return {
            success: false,
            error: "Authentication was cancelled or timed out. Please try again.",
          };
        }
        if (e.name === "SecurityError") {
          return {
            success: false,
            error: "Security error. Please ensure you're on a secure connection.",
          };
        }
      }
      throw e;
    }

    // Step 3: Send credential to server for verification
    const verifyResponse = await fetch(`${API_BASE}/passkeys/authenticate/verify`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        challengeId,
        credential,
      }),
    });

    if (!verifyResponse.ok) {
      const error = await verifyResponse.json();
      // Handle both string detail and Pydantic validation error array format
      let errorMessage = "Authentication failed";
      if (typeof error.detail === "string") {
        errorMessage = error.detail;
      } else if (Array.isArray(error.detail) && error.detail.length > 0) {
        // Pydantic validation error format: [{type, loc, msg, input}, ...]
        errorMessage = error.detail.map((e: { msg: string; loc: string[] }) => 
          `${e.loc?.join(".")}: ${e.msg}`
        ).join("; ");
      }
      return {
        success: false,
        error: errorMessage,
      };
    }

    const result = await verifyResponse.json();
    return {
      success: true,
      accessToken: result.accessToken,
      refreshToken: result.refreshToken,
      tokenType: result.tokenType,
      user: result.user,
    };
  } catch (e) {
    console.error("Passkey authentication error:", e);
    return {
      success: false,
      error: e instanceof Error ? e.message : "An unexpected error occurred",
    };
  }
}

/**
 * Get list of user's registered passkeys
 */
export async function getPasskeys(accessToken: string): Promise<{
  success: boolean;
  passkeys?: PasskeyInfo[];
  error?: string;
}> {
  try {
    const response = await fetch(`${API_BASE}/passkeys/`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.detail || "Failed to get passkeys",
      };
    }

    const result = await response.json();
    return {
      success: true,
      passkeys: result.passkeys,
    };
  } catch (e) {
    console.error("Get passkeys error:", e);
    return {
      success: false,
      error: e instanceof Error ? e.message : "An unexpected error occurred",
    };
  }
}

/**
 * Delete a registered passkey
 */
export async function deletePasskey(
  accessToken: string,
  passkeyId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/passkeys/${passkeyId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      return {
        success: false,
        error: error.detail || "Failed to delete passkey",
      };
    }

    return { success: true };
  } catch (e) {
    console.error("Delete passkey error:", e);
    return {
      success: false,
      error: e instanceof Error ? e.message : "An unexpected error occurred",
    };
  }
}

/**
 * Check if conditional UI (autofill) is available
 * This allows passkeys to appear in the browser's autofill suggestions
 */
export async function isConditionalUIAvailable(): Promise<boolean> {
  if (!isPasskeySupported()) return false;

  try {
    // Check if conditional UI is supported
    if (
      typeof PublicKeyCredential !== "undefined" &&
      typeof (PublicKeyCredential as unknown as { isConditionalMediationAvailable?: () => Promise<boolean> })
        .isConditionalMediationAvailable === "function"
    ) {
      return (PublicKeyCredential as unknown as { isConditionalMediationAvailable: () => Promise<boolean> })
        .isConditionalMediationAvailable();
    }
  } catch {
    // Ignore errors
  }
  return false;
}
