'use client';

import { useTheme } from '@/lib/theme';
import { SunIcon, MoonIcon, ComputerDesktopIcon } from '@heroicons/react/24/outline';
import { useState, useRef, useEffect } from 'react';

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getCurrentIcon = () => {
    if (theme === 'system') {
      return <ComputerDesktopIcon className="h-5 w-5" />;
    }
    return resolvedTheme === 'dark' ? (
      <MoonIcon className="h-5 w-5" />
    ) : (
      <SunIcon className="h-5 w-5" />
    );
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-lg text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        aria-label="Toggle theme"
      >
        {getCurrentIcon()}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-36 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 py-1 z-50">
          <button
            onClick={() => {
              setTheme('light');
              setIsOpen(false);
            }}
            className={`flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
              theme === 'light'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            <SunIcon className="h-4 w-4" />
            Light
          </button>
          <button
            onClick={() => {
              setTheme('dark');
              setIsOpen(false);
            }}
            className={`flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
              theme === 'dark'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            <MoonIcon className="h-4 w-4" />
            Dark
          </button>
          <button
            onClick={() => {
              setTheme('system');
              setIsOpen(false);
            }}
            className={`flex w-full items-center gap-2 px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 ${
              theme === 'system'
                ? 'text-primary-600 dark:text-primary-400'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            <ComputerDesktopIcon className="h-4 w-4" />
            System
          </button>
        </div>
      )}
    </div>
  );
}
