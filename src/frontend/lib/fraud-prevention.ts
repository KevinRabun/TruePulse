/**
 * Device Fingerprinting and Behavioral Analysis for TruePulse
 * 
 * Collects anonymous device and behavior signals to detect bots.
 * No personally identifiable information is collected.
 * 
 * Privacy-focused approach:
 * - All fingerprinting is hashed before transmission
 * - No tracking across different sites
 * - Used only for fraud prevention, not user tracking
 */

// =============================================================================
// Device Fingerprint Collection
// =============================================================================

export interface DeviceFingerprint {
  user_agent: string;
  screen_resolution: string;
  timezone_offset: number;
  language: string;
  platform: string;
  canvas_hash: string | null;
  webgl_vendor: string | null;
  webgl_renderer: string | null;
  audio_hash: string | null;
  hardware_concurrency: number | null;
  device_memory: number | null;
  touch_support: boolean;
  max_touch_points: number;
  plugins_hash: string | null;
  fonts_hash: string | null;
}

export interface BehavioralSignals {
  page_load_to_vote_ms: number;
  time_on_poll_ms: number;
  mouse_move_count: number;
  mouse_click_count: number;
  scroll_count: number;
  changed_choice: boolean;
  viewed_results_preview: boolean;
  expanded_details: boolean;
  is_touch_device: boolean;
  js_execution_time_ms: number | null;
}

/**
 * Simple hash function for fingerprint data.
 * Uses Web Crypto API for consistent hashing.
 */
async function sha256Hash(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const dataBuffer = encoder.encode(data);
  const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Generate canvas fingerprint.
 * Different devices render canvas slightly differently.
 */
async function getCanvasFingerprint(): Promise<string | null> {
  try {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    canvas.width = 200;
    canvas.height = 50;

    // Draw various elements that render differently on different systems
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('TruePulse Verify', 2, 15);
    ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
    ctx.fillText('TruePulse Verify', 4, 17);

    // Add emoji (renders differently on different OS)
    ctx.font = '18px Arial';
    ctx.fillText('🗳️📊', 100, 30);

    const dataUrl = canvas.toDataURL();
    return await sha256Hash(dataUrl);
  } catch {
    return null;
  }
}

/**
 * Get WebGL fingerprint info.
 * GPU and driver info varies by device.
 */
function getWebGLInfo(): { vendor: string | null; renderer: string | null } {
  try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (!gl) return { vendor: null, renderer: null };

    const debugInfo = (gl as WebGLRenderingContext).getExtension('WEBGL_debug_renderer_info');
    if (!debugInfo) return { vendor: null, renderer: null };

    return {
      vendor: (gl as WebGLRenderingContext).getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
      renderer: (gl as WebGLRenderingContext).getParameter(debugInfo.UNMASKED_RENDERER_WEBGL),
    };
  } catch {
    return { vendor: null, renderer: null };
  }
}

/**
 * Get audio fingerprint.
 * Audio processing varies slightly by hardware.
 */
async function getAudioFingerprint(): Promise<string | null> {
  try {
    const AudioContext = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof window.AudioContext }).webkitAudioContext;
    if (!AudioContext) return null;

    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const analyser = context.createAnalyser();
    const gainNode = context.createGain();
    const scriptProcessor = context.createScriptProcessor(4096, 1, 1);

    gainNode.gain.value = 0; // Mute
    oscillator.type = 'triangle';
    oscillator.frequency.value = 10000;

    oscillator.connect(analyser);
    analyser.connect(scriptProcessor);
    scriptProcessor.connect(gainNode);
    gainNode.connect(context.destination);

    oscillator.start(0);

    const fingerprint = await new Promise<string>((resolve) => {
      scriptProcessor.onaudioprocess = (event) => {
        const data = event.inputBuffer.getChannelData(0);
        const sum = data.reduce((acc, val) => acc + Math.abs(val), 0);
        oscillator.stop();
        context.close();
        resolve(sum.toString());
      };
    });

    return await sha256Hash(fingerprint);
  } catch {
    return null;
  }
}

/**
 * Get installed plugins hash.
 */
async function getPluginsHash(): Promise<string | null> {
  try {
    const plugins = navigator.plugins;
    if (!plugins || plugins.length === 0) return null;

    const pluginList = Array.from(plugins)
      .map(p => `${p.name}|${p.filename}`)
      .sort()
      .join(',');

    return await sha256Hash(pluginList);
  } catch {
    return null;
  }
}

/**
 * Collect complete device fingerprint.
 */
export async function collectDeviceFingerprint(): Promise<DeviceFingerprint> {
  const [canvasHash, audioHash, pluginsHash] = await Promise.all([
    getCanvasFingerprint(),
    getAudioFingerprint(),
    getPluginsHash(),
  ]);

  const webglInfo = getWebGLInfo();

  return {
    user_agent: navigator.userAgent,
    screen_resolution: `${screen.width}x${screen.height}`,
    timezone_offset: new Date().getTimezoneOffset(),
    language: navigator.language,
    platform: navigator.platform,
    canvas_hash: canvasHash,
    webgl_vendor: webglInfo.vendor,
    webgl_renderer: webglInfo.renderer,
    audio_hash: audioHash,
    hardware_concurrency: navigator.hardwareConcurrency || null,
    device_memory: (navigator as Navigator & { deviceMemory?: number }).deviceMemory || null,
    touch_support: 'ontouchstart' in window || navigator.maxTouchPoints > 0,
    max_touch_points: navigator.maxTouchPoints || 0,
    plugins_hash: pluginsHash,
    fonts_hash: null, // Requires more complex detection
  };
}

// =============================================================================
// Behavioral Signal Collection
// =============================================================================

/**
 * Behavioral tracker for a single poll interaction.
 * Tracks mouse movements, time on page, etc.
 */
export class BehavioralTracker {
  private startTime: number;
  private pageLoadTime: number;
  private mouseMoves: number = 0;
  private mouseClicks: number = 0;
  private scrolls: number = 0;
  private choiceChanges: number = 0;
  private viewedPreview: boolean = false;
  private expandedDetails: boolean = false;
  private isTouchDevice: boolean;
  private jsStartTime: number;
  private pollId: string;
  private isTracking: boolean = false;
  private boundHandlers: { [key: string]: EventListener } = {};

  constructor(pollId?: string) {
    this.jsStartTime = performance.now();
    this.pageLoadTime = Date.now();
    this.startTime = Date.now();
    this.pollId = pollId || '';
    this.isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
  }

  /**
   * Start tracking behavioral signals.
   */
  startTracking(): void {
    if (this.isTracking) return;
    this.isTracking = true;
    this.startTime = Date.now();
    this.setupEventListeners();
  }

  /**
   * Stop tracking and clean up event listeners.
   */
  stopTracking(): void {
    if (!this.isTracking) return;
    this.isTracking = false;
    
    // Remove event listeners
    if (this.boundHandlers.mousemove) {
      document.removeEventListener('mousemove', this.boundHandlers.mousemove);
    }
    if (this.boundHandlers.click) {
      document.removeEventListener('click', this.boundHandlers.click);
    }
    if (this.boundHandlers.scroll) {
      document.removeEventListener('scroll', this.boundHandlers.scroll);
    }
    this.boundHandlers = {};
  }

  private setupEventListeners(): void {
    // Track mouse movements (throttled)
    let lastMove = 0;
    this.boundHandlers.mousemove = () => {
      const now = Date.now();
      if (now - lastMove > 100) { // Throttle to every 100ms
        this.mouseMoves++;
        lastMove = now;
      }
    };
    document.addEventListener('mousemove', this.boundHandlers.mousemove);

    // Track clicks
    this.boundHandlers.click = () => {
      this.mouseClicks++;
    };
    document.addEventListener('click', this.boundHandlers.click);

    // Track scrolls (throttled)
    let lastScroll = 0;
    this.boundHandlers.scroll = () => {
      const now = Date.now();
      if (now - lastScroll > 200) {
        this.scrolls++;
        lastScroll = now;
      }
    };
    document.addEventListener('scroll', this.boundHandlers.scroll);
  }

  /**
   * Reset timer when poll becomes visible.
   */
  startPollTimer(): void {
    this.startTime = Date.now();
  }

  /**
   * Record that user changed their choice.
   */
  recordChoiceChange(): void {
    this.choiceChanges++;
  }

  /**
   * Record that user viewed results preview.
   */
  recordPreviewView(): void {
    this.viewedPreview = true;
  }

  /**
   * Record that user expanded details.
   */
  recordDetailsExpand(): void {
    this.expandedDetails = true;
  }

  /**
   * Get collected behavioral signals.
   */
  getSignals(): BehavioralSignals {
    const now = Date.now();
    const jsEndTime = performance.now();

    return {
      page_load_to_vote_ms: now - this.pageLoadTime,
      time_on_poll_ms: now - this.startTime,
      mouse_move_count: this.mouseMoves,
      mouse_click_count: this.mouseClicks,
      scroll_count: this.scrolls,
      changed_choice: this.choiceChanges > 0,
      viewed_results_preview: this.viewedPreview,
      expanded_details: this.expandedDetails,
      is_touch_device: this.isTouchDevice,
      js_execution_time_ms: Math.round(jsEndTime - this.jsStartTime),
    };
  }
}

// =============================================================================
// Verification Challenge Handling
// =============================================================================

export type ChallengeType = 'none' | 'captcha' | 'sms_verify' | 'email_verify' | 'block';

export interface RiskAssessment {
  risk_score: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  required_challenge: ChallengeType;
  allow_vote: boolean;
  block_reason?: string;
}

/**
 * Handle challenge requirements before voting.
 */
export async function handleVoteChallenge(
  assessment: RiskAssessment,
  onCaptchaRequired: () => Promise<string | null>,
  onSMSRequired: () => Promise<boolean>,
): Promise<boolean> {
  switch (assessment.required_challenge) {
    case 'none':
      return true;

    case 'captcha':
      const captchaToken = await onCaptchaRequired();
      return captchaToken !== null;

    case 'sms_verify':
      return await onSMSRequired();

    case 'block':
      return false;

    default:
      return true;
  }
}

// =============================================================================
// Vote Request with Fraud Prevention
// =============================================================================

export interface SecureVoteRequest {
  poll_id: string;
  choice_id: string;
  fingerprint: DeviceFingerprint;
  behavioral_signals: BehavioralSignals;
  captcha_token?: string;
}

/**
 * Create a secure vote request with all fraud prevention data.
 */
export async function createSecureVoteRequest(
  pollId: string,
  choiceId: string,
  tracker: BehavioralTracker,
  captchaToken?: string,
): Promise<SecureVoteRequest> {
  const [fingerprint] = await Promise.all([
    collectDeviceFingerprint(),
  ]);

  return {
    poll_id: pollId,
    choice_id: choiceId,
    fingerprint,
    behavioral_signals: tracker.getSignals(),
    captcha_token: captchaToken,
  };
}

// =============================================================================
// Singleton Tracker Instance
// =============================================================================

let globalTracker: BehavioralTracker | null = null;

/**
 * Get or create the global behavioral tracker.
 */
export function getBehavioralTracker(): BehavioralTracker {
  if (!globalTracker) {
    globalTracker = new BehavioralTracker();
  }
  return globalTracker;
}

/**
 * Reset the global tracker (e.g., when navigating to a new poll).
 */
export function resetBehavioralTracker(): void {
  globalTracker = new BehavioralTracker();
}
