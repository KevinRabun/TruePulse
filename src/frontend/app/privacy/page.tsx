'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-linear-to-r from-primary-600 to-primary-700 py-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-bold text-white sm:text-4xl"
          >
            Privacy Policy
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-2 text-primary-100"
          >
            Last updated: December 18, 2025
          </motion.p>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="prose prose-lg dark:prose-invert max-w-none">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Our Commitment to Privacy
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                At TruePulse, privacy isn&apos;t just a feature—it&apos;s a core principle.
                We believe you should be able to participate in public discourse without
                sacrificing your personal information. This policy explains what data we
                collect, why we collect it, and how we protect it.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Information We Collect
              </h2>
              
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                Account Information
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                When you create an account, we collect:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Email address (for account verification and recovery)</li>
                <li>
                  <strong>Phone number (required)</strong> - Used for SMS verification to confirm your identity 
                  and prevent fraudulent accounts. This is mandatory to ensure our &quot;one person = one vote&quot; 
                  policy. We do not use your phone number for marketing purposes.
                </li>
                <li>Display name (can be a pseudonym)</li>
                <li>Password (stored using industry-standard encryption)</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                Voting Data
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                When you vote on polls:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Your vote choice is recorded anonymously</li>
                <li>We store a hash to prevent duplicate voting, not your identity</li>
                <li>Demographic data (if provided) is aggregated and never linked to individuals</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                Technical Data
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                We automatically collect:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Device type and browser information (for compatibility)</li>
                <li>IP address (for fraud prevention, deleted after 24 hours)</li>
                <li>Usage patterns (aggregated, not individual)</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                How We Use Your Information
              </h2>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400">
                <li><strong>Account Management:</strong> To create and maintain your account</li>
                <li><strong>Fraud Prevention:</strong> To ensure one-person-one-vote integrity</li>
                <li><strong>Service Improvement:</strong> To understand how users interact with our platform</li>
                <li><strong>Communication:</strong> To send important account and service updates</li>
                <li><strong>Aggregated Analytics:</strong> To provide public opinion insights (never individually identifiable)</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                What We Don&apos;t Do
              </h2>
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
                <ul className="space-y-2 text-gray-700 dark:text-gray-300">
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">✓</span>
                    We never sell your personal data to third parties
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">✓</span>
                    We never share individual voting records
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">✓</span>
                    We never use your data for targeted advertising
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">✓</span>
                    We never track you across other websites
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-600 font-bold">✓</span>
                    We never retain IP addresses longer than 24 hours
                  </li>
                </ul>
              </div>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Data Security
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                We employ industry-leading security measures to protect your data:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>End-to-end encryption for all data in transit (TLS 1.3)</li>
                <li>AES-256 encryption for data at rest</li>
                <li>Regular security audits and penetration testing</li>
                <li>Multi-factor authentication options</li>
                <li>Secure, geographically distributed data centers</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Your Rights
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                You have the right to:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li><strong>Access:</strong> Request a copy of all data we have about you</li>
                <li><strong>Correction:</strong> Update or correct your personal information</li>
                <li><strong>Deletion:</strong> Request permanent deletion of your account and data</li>
                <li><strong>Portability:</strong> Export your data in a machine-readable format</li>
                <li><strong>Opt-out:</strong> Unsubscribe from non-essential communications</li>
              </ul>
              <p className="text-gray-600 dark:text-gray-400 mt-4">
                To exercise any of these rights, visit your{' '}
                <a href="/profile" className="text-primary-600 hover:text-primary-700">
                  profile settings
                </a>{' '}
                or contact us through{' '}
                <a href="https://github.com/KevinRabun/TruePulse/discussions" className="text-primary-600 hover:text-primary-700">
                  GitHub Discussions
                </a>
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Cookies
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                We use minimal, essential cookies:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li><strong>Session cookies:</strong> To keep you logged in</li>
                <li><strong>Security cookies:</strong> To prevent cross-site request forgery</li>
                <li><strong>Preference cookies:</strong> To remember your settings (dark mode, etc.)</li>
              </ul>
              <p className="text-gray-600 dark:text-gray-400 mt-4">
                We do not use advertising cookies or third-party tracking cookies.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Third-Party Services
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                We use the following third-party services:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li><strong>Cloudflare Turnstile:</strong> For bot protection (privacy-focused CAPTCHA alternative)</li>
                <li><strong>Microsoft Azure:</strong> For cloud infrastructure (data processing agreement in place)</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                International Data Transfers
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Your data may be processed in data centers located in the United States
                and European Union. We ensure appropriate safeguards through Standard
                Contractual Clauses and compliance with GDPR requirements.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Children&apos;s Privacy
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                TruePulse is not intended for users under 13 years of age. We do not
                knowingly collect personal information from children. If you believe
                a child has provided us with personal information, please contact us
                immediately.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Changes to This Policy
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                We may update this policy from time to time. We will notify you of
                significant changes via email or a prominent notice on our website.
                Continued use of TruePulse after changes constitutes acceptance of
                the updated policy.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Contact Us
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                If you have questions about this Privacy Policy or our data practices,
                please contact us:
              </p>
              <div className="mt-4 bg-gray-100 dark:bg-gray-800 rounded-lg p-6">
                <p className="text-gray-700 dark:text-gray-300">
                  <strong>GitHub:</strong>{' '}
                  <a href="https://github.com/KevinRabun/TruePulse/discussions" className="text-primary-600 hover:text-primary-700">
                    TruePulse Discussions
                  </a>
                </p>
                <p className="text-gray-700 dark:text-gray-300 mt-2">
                  <strong>Website:</strong>{' '}
                  <a href="https://truepulse.net" className="text-primary-600 hover:text-primary-700">
                    truepulse.net
                  </a>
                </p>
              </div>
            </section>
          </motion.div>
        </div>

        {/* Back Link */}
        <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700">
          <Link
            href="/"
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
