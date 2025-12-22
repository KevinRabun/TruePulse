'use client';

import Link from 'next/link';
import { useState, useRef, useEffect } from 'react';
import { Menu, X, User, BarChart3, LogOut, Settings, Trophy } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/ui/toast';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, isAuthenticated, logout } = useAuth();
  const { success } = useToast();
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    setUserMenuOpen(false);
    success('Signed out', 'You have been signed out successfully.');
  };

  return (
    <header className="bg-white dark:bg-gray-800 shadow-xs sticky top-0 z-50">
      <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <BarChart3 className="h-8 w-8 text-primary-600" />
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                TruePulse
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:space-x-8">
            <Link
              href="/polls"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
            >
              Polls
            </Link>
            <Link
              href="/achievements"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
            >
              Achievements
            </Link>
            <Link
              href="/leaderboard"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
            >
              Leaderboard
            </Link>
            <Link
              href="/about"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
            >
              About
            </Link>
          </div>

          {/* Auth Buttons / User Menu */}
          <div className="hidden md:flex md:items-center md:space-x-4">
            {isAuthenticated && user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                  className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {/* Avatar */}
                  <div className="h-8 w-8 rounded-full bg-linear-to-r from-purple-500 to-cyan-500 flex items-center justify-center text-white font-semibold text-sm">
                    {user.display_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || 'U'}
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {user.display_name || user.username || 'User'}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center">
                      <Trophy className="h-3 w-3 mr-1 text-yellow-500" />
                      {user.points?.toLocaleString() || 0} points
                    </p>
                  </div>
                </button>

                {/* Dropdown Menu */}
                {userMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 py-1 z-50">
                    <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {user.display_name || user.username}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {user.email}
                      </p>
                    </div>
                    <Link
                      href="/profile"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <User className="h-4 w-4 mr-3" />
                      Profile
                    </Link>
                    <Link
                      href="/profile?tab=settings"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <Settings className="h-4 w-4 mr-3" />
                      Settings
                    </Link>
                    <Link
                      href="/leaderboard"
                      onClick={() => setUserMenuOpen(false)}
                      className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <Trophy className="h-4 w-4 mr-3" />
                      Leaderboard
                    </Link>
                    <div className="border-t border-gray-100 dark:border-gray-700 mt-1">
                      <button
                        onClick={handleLogout}
                        className="flex w-full items-center px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        <LogOut className="h-4 w-4 mr-3" />
                        Sign out
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <>
                <Link
                  href="/login"
                  className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white font-medium"
                >
                  Sign in
                </Link>
                <Link
                  href="/register"
                  className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-hidden focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Get Started
                </Link>
              </>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="flex md:hidden">
            <button
              type="button"
              className="text-gray-600 hover:text-gray-900 dark:text-gray-300"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 space-y-4">
            {isAuthenticated && user && (
              <div className="flex items-center space-x-3 pb-4 border-b border-gray-200 dark:border-gray-700">
                <div className="h-10 w-10 rounded-full bg-linear-to-r from-purple-500 to-cyan-500 flex items-center justify-center text-white font-semibold">
                  {user.display_name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase() || 'U'}
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {user.display_name || user.username || 'User'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
                    <Trophy className="h-3 w-3 mr-1 text-yellow-500" />
                    {user.points?.toLocaleString() || 0} points
                  </p>
                </div>
              </div>
            )}
            <Link
              href="/polls"
              className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Polls
            </Link>
            <Link
              href="/achievements"
              className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Achievements
            </Link>
            <Link
              href="/leaderboard"
              className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              Leaderboard
            </Link>
            <Link
              href="/about"
              className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
              onClick={() => setMobileMenuOpen(false)}
            >
              About
            </Link>
            <div className="pt-4 border-t border-gray-200 dark:border-gray-700 space-y-4">
              {isAuthenticated && user ? (
                <>
                  <Link
                    href="/profile"
                    className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Profile
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout();
                      setMobileMenuOpen(false);
                    }}
                    className="block w-full text-left text-red-600 dark:text-red-400 font-medium"
                  >
                    Sign out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    href="/login"
                    className="block text-gray-600 hover:text-gray-900 dark:text-gray-300 font-medium"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    className="block w-full text-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </nav>
    </header>
  );
}
