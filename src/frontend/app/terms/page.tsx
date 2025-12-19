'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-700 py-12">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-3xl font-bold text-white sm:text-4xl"
          >
            Terms of Service
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
                1. Acceptance of Terms
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                By accessing or using TruePulse (&quot;the Service&quot;), you agree to be bound
                by these Terms of Service (&quot;Terms&quot;). If you do not agree to these Terms,
                you may not use the Service. We reserve the right to update these Terms
                at any time, and your continued use of the Service constitutes acceptance
                of any changes.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                2. Description of Service
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                TruePulse is an AI-powered polling platform that generates unbiased poll
                questions from current events and allows users to vote and view aggregated
                public opinion data. The Service includes:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Access to AI-generated polls on current events</li>
                <li>Ability to vote on polls (one vote per user per poll)</li>
                <li>View aggregated, anonymized results</li>
                <li>Gamification features including points and leaderboards</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                3. User Accounts
              </h2>
              
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                3.1 Account Creation
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                To access certain features, you must create an account. You agree to:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Provide accurate and complete registration information</li>
                <li>Maintain the security of your account credentials</li>
                <li>Promptly notify us of any unauthorized access</li>
                <li>Be responsible for all activities under your account</li>
              </ul>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                3.2 Account Requirements
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                You must be at least 13 years old to create an account. If you are under
                18, you represent that you have your parent or guardian&apos;s permission to
                use the Service.
              </p>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                3.3 Account Termination
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                We reserve the right to suspend or terminate accounts that violate these
                Terms or engage in fraudulent activity. You may delete your account at
                any time through your account settings.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                4. Acceptable Use
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                You agree not to:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Create multiple accounts to vote more than once on a poll</li>
                <li>Use bots, scripts, or automated tools to interact with the Service</li>
                <li>Attempt to manipulate poll results through any means</li>
                <li>Circumvent fraud prevention measures</li>
                <li>Harvest or collect user data without authorization</li>
                <li>Interfere with or disrupt the Service or servers</li>
                <li>Impersonate another person or entity</li>
                <li>Use the Service for any illegal purpose</li>
                <li>Violate any applicable laws or regulations</li>
              </ul>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                5. Voting Integrity
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                The integrity of our polling data is paramount. We employ various
                measures to ensure one-person-one-vote:
              </p>
              <ul className="list-disc pl-6 text-gray-600 dark:text-gray-400 mt-2">
                <li>Email and/or phone verification</li>
                <li>Device fingerprinting</li>
                <li>Behavioral analysis</li>
                <li>CAPTCHA challenges</li>
              </ul>
              <p className="text-gray-600 dark:text-gray-400 mt-4">
                Attempts to circumvent these measures may result in immediate account
                termination and potential legal action.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                6. Intellectual Property
              </h2>
              
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                6.1 Our Content
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                The Service, including its design, features, and content (excluding
                user-generated content), is owned by TruePulse and protected by copyright,
                trademark, and other intellectual property laws. Our open-source code is
                licensed under the MIT License.
              </p>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                6.2 Poll Data
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Aggregated poll results are made available under a Creative Commons
                Attribution 4.0 International License (CC BY 4.0). You may use, share,
                and adapt this data with appropriate attribution.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                7. Disclaimers
              </h2>
              
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                7.1 Service Availability
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                The Service is provided &quot;as is&quot; and &quot;as available.&quot; We do not guarantee
                uninterrupted or error-free operation. We may modify, suspend, or
                discontinue any aspect of the Service at any time.
              </p>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                7.2 Poll Accuracy
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                While we strive for unbiased polling, we make no guarantees about the
                accuracy, completeness, or representativeness of poll results. Poll
                data should not be used as the sole basis for important decisions.
              </p>

              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mt-6 mb-3">
                7.3 AI-Generated Content
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Poll questions are generated by artificial intelligence. While we employ
                safeguards to ensure balance and accuracy, AI-generated content may
                occasionally contain errors or unintended biases.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                8. Limitation of Liability
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                To the maximum extent permitted by law, TruePulse and its affiliates,
                officers, employees, and agents shall not be liable for any indirect,
                incidental, special, consequential, or punitive damages arising from
                your use of the Service. Our total liability shall not exceed the
                amount you paid us in the past 12 months, or $100, whichever is greater.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                9. Indemnification
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                You agree to indemnify and hold harmless TruePulse and its affiliates
                from any claims, damages, losses, or expenses arising from your use
                of the Service, violation of these Terms, or infringement of any
                third-party rights.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                10. Dispute Resolution
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Any disputes arising from these Terms or your use of the Service shall
                be resolved through binding arbitration in accordance with the rules
                of the American Arbitration Association. You waive any right to
                participate in class actions.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                11. Governing Law
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                These Terms shall be governed by and construed in accordance with the
                laws of the State of Delaware, United States, without regard to its
                conflict of law provisions.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                12. Changes to Terms
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                We may modify these Terms at any time. Material changes will be
                communicated via email or a prominent notice on the Service. Continued
                use after changes constitutes acceptance. If you disagree with changes,
                you must stop using the Service and delete your account.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                13. Severability
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                If any provision of these Terms is found to be unenforceable, the
                remaining provisions shall continue in full force and effect.
              </p>
            </section>

            <section className="mb-12">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                14. Contact Information
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                For questions about these Terms, please contact us:
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
