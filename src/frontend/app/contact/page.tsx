'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  EnvelopeIcon,
  ChatBubbleLeftRightIcon,
  ShieldCheckIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';
import { Github } from 'lucide-react';

const contactMethods = [
  {
    icon: ChatBubbleLeftRightIcon,
    title: 'Community Discussions',
    description: 'Ask questions, share ideas, and connect with other users on GitHub Discussions.',
    link: 'https://github.com/KevinRabun/TruePulse/discussions',
    linkText: 'Join the Discussion',
    external: true,
  },
  {
    icon: Github,
    title: 'Report Issues',
    description: 'Found a bug or have a feature request? Open an issue on our GitHub repository.',
    link: 'https://github.com/KevinRabun/TruePulse/issues',
    linkText: 'Open an Issue',
    external: true,
  },
  {
    icon: ShieldCheckIcon,
    title: 'Security Concerns',
    description: 'For security vulnerabilities, please report responsibly through our security policy.',
    link: 'https://github.com/KevinRabun/TruePulse/security/policy',
    linkText: 'Security Policy',
    external: true,
  },
  {
    icon: EnvelopeIcon,
    title: 'General Inquiries',
    description: 'For business inquiries, partnerships, or press, reach out via email.',
    link: 'mailto:contact@truepulse.net',
    linkText: 'contact@truepulse.net',
    external: true,
  },
];

const quickLinks = [
  {
    icon: DocumentTextIcon,
    title: 'Terms of Service',
    description: 'Read our terms and conditions.',
    link: '/terms',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Privacy Policy',
    description: 'Learn how we protect your data.',
    link: '/privacy',
  },
];

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl font-bold text-white sm:text-5xl"
          >
            Contact Us
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-4 text-xl text-primary-100 max-w-3xl mx-auto"
          >
            Have questions, feedback, or need support? We&apos;re here to help.
          </motion.p>
        </div>
      </div>

      {/* Contact Methods */}
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-8 md:grid-cols-2">
          {contactMethods.map((method, index) => (
            <motion.div
              key={method.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900">
                    <method.icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {method.title}
                  </h3>
                  <p className="mt-2 text-gray-600 dark:text-gray-400">
                    {method.description}
                  </p>
                  <a
                    href={method.link}
                    target={method.external ? '_blank' : undefined}
                    rel={method.external ? 'noopener noreferrer' : undefined}
                    className="mt-4 inline-flex items-center text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium"
                  >
                    {method.linkText}
                    {method.external && (
                      <svg
                        className="ml-1 h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                        />
                      </svg>
                    )}
                  </a>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Quick Links Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mt-16"
        >
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-8">
            Quick Links
          </h2>
          <div className="grid gap-6 md:grid-cols-2 max-w-2xl mx-auto">
            {quickLinks.map((link) => (
              <Link
                key={link.title}
                href={link.link}
                className="flex items-center space-x-4 bg-white dark:bg-gray-800 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700">
                  <link.icon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                </div>
                <div>
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    {link.title}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {link.description}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </motion.div>

        {/* Response Time Notice */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="mt-16 text-center"
        >
          <div className="inline-flex items-center rounded-full bg-primary-50 dark:bg-primary-900/30 px-6 py-3">
            <span className="text-sm text-primary-700 dark:text-primary-300">
              We typically respond to inquiries within 24-48 hours during business days.
            </span>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
