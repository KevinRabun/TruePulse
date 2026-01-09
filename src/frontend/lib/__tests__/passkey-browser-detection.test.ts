/**
 * Tests for iOS browser detection utilities in passkey.ts
 */

import { isIOSDevice, isIOSSafari, getIOSBrowserName, getPasskeyBrowserWarning } from '../passkey';

// Save original navigator
const originalNavigator = global.navigator;

// Helper to mock navigator
function mockNavigator(overrides: Partial<Navigator>) {
  Object.defineProperty(global, 'navigator', {
    value: { ...originalNavigator, ...overrides },
    writable: true,
    configurable: true,
  });
}

// Helper to restore navigator
function restoreNavigator() {
  Object.defineProperty(global, 'navigator', {
    value: originalNavigator,
    writable: true,
    configurable: true,
  });
}

describe('iOS Device Detection', () => {
  afterEach(() => {
    restoreNavigator();
  });

  describe('isIOSDevice', () => {
    it('returns true for iPhone user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(isIOSDevice()).toBe(true);
    });

    it('returns true for iPad user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        platform: 'iPad',
        maxTouchPoints: 5,
      });
      expect(isIOSDevice()).toBe(true);
    });

    it('returns true for iPad in desktop mode (MacIntel with touch)', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        platform: 'MacIntel',
        maxTouchPoints: 5,
      });
      expect(isIOSDevice()).toBe(true);
    });

    it('returns false for Mac desktop (no touch)', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        platform: 'MacIntel',
        maxTouchPoints: 0,
      });
      expect(isIOSDevice()).toBe(false);
    });

    it('returns false for Android device', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        platform: 'Linux armv81',
        maxTouchPoints: 5,
      });
      expect(isIOSDevice()).toBe(false);
    });

    it('returns false for Windows desktop', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        platform: 'Win32',
        maxTouchPoints: 0,
      });
      expect(isIOSDevice()).toBe(false);
    });
  });

  describe('isIOSSafari', () => {
    it('returns true for Safari on iPhone', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(isIOSSafari()).toBe(true);
    });

    it('returns false for Chrome on iPhone', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(isIOSSafari()).toBe(false);
    });

    it('returns false for Edge on iPhone', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 EdgiOS/120.0.2210.150 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(isIOSSafari()).toBe(false);
    });

    it('returns false for Firefox on iPhone', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/120.0 Mobile/15E148 Safari/605.1.15',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(isIOSSafari()).toBe(false);
    });

    it('returns false for non-iOS device', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        platform: 'Win32',
        maxTouchPoints: 0,
      });
      expect(isIOSSafari()).toBe(false);
    });
  });

  describe('getIOSBrowserName', () => {
    it('returns Chrome for CriOS user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(getIOSBrowserName()).toBe('Chrome');
    });

    it('returns Edge for EdgiOS user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 EdgiOS/120.0.2210.150 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(getIOSBrowserName()).toBe('Edge');
    });

    it('returns Firefox for FxiOS user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/120.0 Mobile/15E148 Safari/605.1.15',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(getIOSBrowserName()).toBe('Firefox');
    });

    it('returns Safari for Safari user agent', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(getIOSBrowserName()).toBe('Safari');
    });

    it('returns null for non-iOS device', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        platform: 'Win32',
        maxTouchPoints: 0,
      });
      expect(getIOSBrowserName()).toBe(null);
    });
  });

  describe('getPasskeyBrowserWarning', () => {
    it('returns null for Safari on iOS', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      expect(getPasskeyBrowserWarning()).toBe(null);
    });

    it('returns warning for Chrome on iOS', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      const warning = getPasskeyBrowserWarning();
      expect(warning).not.toBe(null);
      expect(warning?.browserName).toBe('Chrome');
      expect(warning?.message).toContain('Safari');
    });

    it('returns warning for Edge on iOS', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 EdgiOS/120.0.2210.150 Mobile/15E148 Safari/604.1',
        platform: 'iPhone',
        maxTouchPoints: 5,
      });
      const warning = getPasskeyBrowserWarning();
      expect(warning).not.toBe(null);
      expect(warning?.browserName).toBe('Edge');
      expect(warning?.message).toContain('Safari');
    });

    it('returns null for non-iOS device', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        platform: 'Win32',
        maxTouchPoints: 0,
      });
      expect(getPasskeyBrowserWarning()).toBe(null);
    });

    it('returns null for Chrome on Android', () => {
      mockNavigator({
        userAgent: 'Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        platform: 'Linux armv81',
        maxTouchPoints: 5,
      });
      expect(getPasskeyBrowserWarning()).toBe(null);
    });
  });
});
