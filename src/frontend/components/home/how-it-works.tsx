'use client';

import { motion } from 'framer-motion';
import { Newspaper, Cpu, Vote, BarChart2 } from 'lucide-react';

const steps = [
  {
    icon: Newspaper,
    title: 'News Aggregation',
    description:
      'Our AI continuously monitors multiple news sources to identify trending topics from diverse perspectives.',
  },
  {
    icon: Cpu,
    title: 'Unbiased Question Generation',
    description:
      'Using advanced NLP, we generate poll questions that are neutral, fair, and represent all viewpoints.',
  },
  {
    icon: Vote,
    title: 'Private Voting',
    description:
      'Cast your vote with confidence. Cryptographic techniques ensure your vote is counted but never traced.',
  },
  {
    icon: BarChart2,
    title: 'Aggregated Insights',
    description:
      'View real-time results and demographic breakdowns without compromising individual privacy.',
  },
];

export function HowItWorks() {
  return (
    <section className="py-16 bg-white dark:bg-gray-800">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            How TruePulse Works
          </h2>
          <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            From current events to public opinion insights, all while protecting your privacy
          </p>
        </div>

        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.15 }}
              viewport={{ once: true }}
              className="relative"
            >
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-12 left-1/2 w-full h-0.5 bg-gray-200 dark:bg-gray-700" />
              )}

              <div className="relative flex flex-col items-center text-center">
                {/* Step number */}
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 w-6 h-6 rounded-full bg-primary-600 text-white text-sm font-bold flex items-center justify-center">
                  {index + 1}
                </div>

                {/* Icon */}
                <div className="w-24 h-24 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-4">
                  <step.icon className="w-10 h-10 text-primary-600 dark:text-primary-400" />
                </div>

                {/* Content */}
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {step.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {step.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
