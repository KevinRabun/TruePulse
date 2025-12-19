'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  ShieldCheckIcon,
  SparklesIcon,
  UserGroupIcon,
  GlobeAltIcon,
  ChartBarIcon,
  LockClosedIcon,
  CodeBracketIcon,
  HeartIcon,
} from '@heroicons/react/24/outline';
import { api, type FormattedStats } from '@/lib/api';

const values = [
  {
    icon: ShieldCheckIcon,
    title: 'Unbiased by Design',
    description:
      'Our AI generates poll questions from multiple perspectives, ensuring balanced representation of viewpoints without editorial bias.',
  },
  {
    icon: LockClosedIcon,
    title: 'Privacy First',
    description:
      'We collect only what\'s necessary. Your votes are anonymous, and we never sell your data to third parties.',
  },
  {
    icon: SparklesIcon,
    title: 'AI-Powered Transparency',
    description:
      'Every poll shows its source material and AI reasoning, so you can understand how questions were formulated.',
  },
  {
    icon: CodeBracketIcon,
    title: 'Open Source',
    description:
      'Our platform is open source. Anyone can inspect our code, suggest improvements, or build upon our work.',
  },
];

// Default stats shown while loading or on error
const defaultStats = [
  { label: 'Daily Active Users', value: '—' },
  { label: 'Polls Generated', value: '—' },
  { label: 'Countries Reached', value: '—' },
  { label: 'Votes Cast', value: '—' },
];

const team = [
  {
    name: 'Open Source Community',
    role: 'Contributors',
    description: 'TruePulse is built and maintained by a passionate community of developers, designers, and democracy advocates.',
  },
];

export default function AboutPage() {
  const [stats, setStats] = useState(defaultStats);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.getPlatformStats();
        const apiStats = response.stats;
        setStats([
          { label: 'Daily Active Users', value: apiStats.active_users },
          { label: 'Polls Generated', value: apiStats.polls_created },
          { label: 'Countries Reached', value: apiStats.countries_represented_raw > 0 ? String(apiStats.countries_represented_raw) : '—' },
          { label: 'Votes Cast', value: apiStats.votes_cast },
        ]);
      } catch (error) {
        console.error('Failed to fetch platform stats:', error);
        // Keep default stats on error
      } finally {
        setIsLoading(false);
      }
    };
    fetchStats();
  }, []);

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
            About TruePulse
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-4 text-xl text-primary-100 max-w-3xl mx-auto"
          >
            We&apos;re building the most transparent and unbiased polling platform
            on the internet, powered by AI and guided by democratic principles.
          </motion.p>
        </div>
      </div>

      {/* Mission Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                Our Mission
              </h2>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                In an era of polarization and media bias, we believe everyone deserves
                access to fair, balanced information about public opinion. TruePulse
                uses artificial intelligence to generate poll questions from current
                events, ensuring multiple perspectives are represented without
                editorial influence.
              </p>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                We&apos;re not trying to tell you what to think. We&apos;re trying to
                help you understand what others think—and to add your voice to the
                conversation.
              </p>
              <div className="mt-8">
                <Link
                  href="/polls"
                  className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition-colors"
                >
                  Explore Polls
                  <ChartBarIcon className="ml-2 h-5 w-5" />
                </Link>
              </div>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="grid grid-cols-2 gap-4">
                {stats.map((stat, index) => (
                  <motion.div
                    key={stat.label}
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                    viewport={{ once: true }}
                    className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md text-center"
                  >
                    <div className={`text-3xl font-bold text-primary-600 ${isLoading ? 'animate-pulse' : ''}`}>
                      {stat.value}
                    </div>
                    <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                      {stat.label}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="py-16 sm:py-24 bg-white dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Our Values
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              These principles guide every decision we make, from algorithm design
              to user experience.
            </p>
          </div>

          <div className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {values.map((value, index) => (
              <motion.div
                key={value.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="text-center"
              >
                <div className="mx-auto h-12 w-12 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                  <value.icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-gray-900 dark:text-white">
                  {value.title}
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  {value.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              How TruePulse Works
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Our AI-powered process ensures every poll is fair, balanced, and
              relevant.
            </p>
          </div>

          <div className="mt-12 space-y-12">
            {[
              {
                step: '01',
                title: 'News Aggregation',
                description:
                  'Our system continuously monitors trusted news sources across the political spectrum, identifying trending topics and current events.',
                icon: GlobeAltIcon,
              },
              {
                step: '02',
                title: 'AI Analysis',
                description:
                  'Advanced AI analyzes each story from multiple angles, identifying the key questions and ensuring all perspectives are represented.',
                icon: SparklesIcon,
              },
              {
                step: '03',
                title: 'Poll Generation',
                description:
                  'Questions are generated with carefully balanced answer choices that avoid leading language or implicit bias.',
                icon: ChartBarIcon,
              },
              {
                step: '04',
                title: 'Community Voting',
                description:
                  'Users vote anonymously, with fraud prevention measures ensuring one person, one vote integrity.',
                icon: UserGroupIcon,
              },
            ].map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className={`flex flex-col md:flex-row items-center gap-8 ${
                  index % 2 === 1 ? 'md:flex-row-reverse' : ''
                }`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-4">
                    <span className="text-5xl font-bold text-primary-200 dark:text-primary-800">
                      {item.step}
                    </span>
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                      {item.title}
                    </h3>
                  </div>
                  <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                    {item.description}
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <div className="h-24 w-24 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                    <item.icon className="h-12 w-12 text-primary-600 dark:text-primary-400" />
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Open Source Section */}
      <section className="py-16 sm:py-24 bg-gray-900 text-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <CodeBracketIcon className="mx-auto h-12 w-12 text-primary-400" />
          <h2 className="mt-4 text-3xl font-bold">Open Source & Transparent</h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            TruePulse is fully open source. Our code, algorithms, and methodology
            are available for anyone to inspect, audit, and improve. Transparency
            isn&apos;t just a feature—it&apos;s our foundation.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://github.com/truepulse"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-gray-900 bg-white hover:bg-gray-100 transition-colors"
            >
              View on GitHub
              <CodeBracketIcon className="ml-2 h-5 w-5" />
            </a>
            <Link
              href="/methodology"
              className="inline-flex items-center px-6 py-3 border border-white text-base font-medium rounded-lg text-white hover:bg-white/10 transition-colors"
            >
              Read Our Methodology
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <HeartIcon className="mx-auto h-12 w-12 text-red-500" />
          <h2 className="mt-4 text-3xl font-bold text-gray-900 dark:text-white">
            Join the Movement
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Help us build a more informed democracy. Every vote counts, and every
            voice matters.
          </p>
          <div className="mt-8">
            <Link
              href="/register"
              className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition-colors"
            >
              Create Your Free Account
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
