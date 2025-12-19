'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  ShieldCheckIcon,
  LockClosedIcon,
  KeyIcon,
  ServerIcon,
  EyeSlashIcon,
  DocumentCheckIcon,
  BugAntIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';

const securityFeatures = [
  {
    icon: LockClosedIcon,
    title: 'Encryption in Transit',
    description:
      'All data transmitted between your device and our servers is encrypted using TLS 1.3, the latest and most secure transport protocol.',
  },
  {
    icon: ServerIcon,
    title: 'Encryption at Rest',
    description:
      'Your data is encrypted at rest using AES-256, the same standard used by governments and financial institutions worldwide.',
  },
  {
    icon: KeyIcon,
    title: 'Secure Authentication',
    description:
      'We support multi-factor authentication (MFA), secure password hashing with Argon2, and protection against brute-force attacks.',
  },
  {
    icon: EyeSlashIcon,
    title: 'Anonymous Voting',
    description:
      'Votes are cryptographically separated from user identities. Even we cannot link a specific vote to a specific user.',
  },
  {
    icon: ShieldCheckIcon,
    title: 'Fraud Prevention',
    description:
      'Advanced algorithms detect and prevent vote manipulation, multiple accounts, and bot activity without compromising privacy.',
  },
  {
    icon: DocumentCheckIcon,
    title: 'Regular Audits',
    description:
      'Our systems undergo regular security audits and penetration testing by independent third-party security firms.',
  },
];

const certifications = [
  {
    name: 'SOC 2 Type II',
    description: 'Certified for security, availability, and confidentiality controls',
    status: 'Certified',
  },
  {
    name: 'GDPR',
    description: 'Fully compliant with European data protection regulations',
    status: 'Compliant',
  },
  {
    name: 'CCPA',
    description: 'Compliant with California Consumer Privacy Act requirements',
    status: 'Compliant',
  },
  {
    name: 'ISO 27001',
    description: 'Information security management certification',
    status: 'In Progress',
  },
];

export default function SecurityPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-gray-900 to-gray-800 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto h-16 w-16 rounded-full bg-green-500/20 flex items-center justify-center mb-6"
          >
            <ShieldCheckIcon className="h-8 w-8 text-green-400" />
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl font-bold text-white sm:text-5xl"
          >
            Security at TruePulse
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-4 text-xl text-gray-300 max-w-3xl mx-auto"
          >
            Your trust is our foundation. We employ industry-leading security
            practices to protect your data and ensure the integrity of every vote.
          </motion.p>
        </div>
      </div>

      {/* Security Features */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              How We Protect You
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Security isn&apos;t an afterthought—it&apos;s built into every layer of our platform.
            </p>
          </div>

          <div className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-3">
            {securityFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md"
              >
                <div className="h-12 w-12 rounded-lg bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                  <feature.icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Infrastructure Section */}
      <section className="py-16 sm:py-24 bg-white dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                Robust Infrastructure
              </h2>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                TruePulse runs on Microsoft Azure, benefiting from world-class
                physical security, redundancy, and compliance certifications.
              </p>
              <ul className="mt-6 space-y-4">
                {[
                  'Geographically distributed data centers',
                  'Automatic failover and disaster recovery',
                  'High availability architecture',
                  'DDoS protection and Web Application Firewall',
                  'Real-time threat monitoring and alerting',
                  'Network isolation and private endpoints',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <ShieldCheckIcon className="h-6 w-6 text-green-500 flex-shrink-0" />
                    <span className="text-gray-600 dark:text-gray-400">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="bg-gray-900 rounded-2xl p-8 text-center">
                <div className="text-6xl font-bold text-green-400">99.9%</div>
                <div className="mt-2 text-gray-400">Uptime Guarantee</div>
                <div className="mt-8 grid grid-cols-2 gap-4">
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-2xl font-bold text-white">0</div>
                    <div className="text-sm text-gray-400">Data Breaches</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-2xl font-bold text-white">24/7</div>
                    <div className="text-sm text-gray-400">Monitoring</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-2xl font-bold text-white">&lt;15min</div>
                    <div className="text-sm text-gray-400">Incident Response</div>
                  </div>
                  <div className="bg-gray-800 rounded-lg p-4">
                    <div className="text-2xl font-bold text-white">256-bit</div>
                    <div className="text-sm text-gray-400">Encryption</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Certifications */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Compliance & Certifications
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              We maintain rigorous compliance with industry standards and regulations.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {certifications.map((cert, index) => (
              <motion.div
                key={cert.name}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {cert.name}
                  </h3>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      cert.status === 'Certified'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : cert.status === 'Compliant'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                    }`}
                  >
                    {cert.status}
                  </span>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {cert.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Bug Bounty Section */}
      <section className="py-16 sm:py-24 bg-gray-900 text-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <div className="flex items-center gap-3 mb-4">
                <BugAntIcon className="h-8 w-8 text-primary-400" />
                <h2 className="text-3xl font-bold">Bug Bounty Program</h2>
              </div>
              <p className="text-lg text-gray-300">
                We believe in the power of the security community. Our bug bounty
                program rewards researchers who responsibly disclose security
                vulnerabilities.
              </p>
              <div className="mt-8 space-y-4">
                <div className="flex items-center gap-4">
                  <div className="text-2xl font-bold text-primary-400">$100 - $10,000</div>
                  <div className="text-gray-400">Bounty Range</div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-2xl font-bold text-primary-400">48 hours</div>
                  <div className="text-gray-400">Initial Response Time</div>
                </div>
              </div>
              <div className="mt-8">
                <a
                  href="https://github.com/KevinRabun/TruePulse/security/advisories/new"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition-colors"
                >
                  Report a Vulnerability
                  <EnvelopeIcon className="ml-2 h-5 w-5" />
                </a>
              </div>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="bg-gray-800 rounded-xl p-6">
                <h3 className="text-lg font-semibold mb-4">In Scope</h3>
                <ul className="space-y-2 text-gray-300">
                  <li>• Authentication and session management</li>
                  <li>• Vote manipulation vulnerabilities</li>
                  <li>• Data exposure or leakage</li>
                  <li>• Cross-site scripting (XSS)</li>
                  <li>• SQL injection</li>
                  <li>• API security issues</li>
                </ul>
                <h3 className="text-lg font-semibold mt-6 mb-4">Out of Scope</h3>
                <ul className="space-y-2 text-gray-400">
                  <li>• Social engineering attacks</li>
                  <li>• Denial of service (DoS/DDoS)</li>
                  <li>• Physical security issues</li>
                  <li>• Third-party services</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Contact Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Security Questions?
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
            Our security team is here to help. Reach out with any concerns or inquiries.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://github.com/KevinRabun/TruePulse/security/advisories/new"
              className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition-colors"
            >
              Report Security Issue
            </a>
            <Link
              href="/privacy"
              className="inline-flex items-center justify-center px-6 py-3 border border-gray-300 dark:border-gray-600 text-base font-medium rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              View Privacy Policy
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
