'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import {
  SparklesIcon,
  NewspaperIcon,
  ScaleIcon,
  ChartBarIcon,
  ShieldCheckIcon,
  EyeIcon,
  BeakerIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline';

const steps = [
  {
    number: '01',
    icon: NewspaperIcon,
    title: 'News Aggregation',
    description:
      'We continuously monitor hundreds of news sources across the political spectrum, including mainstream media, independent journalism, and international outlets.',
    details: [
      'Sources rated for political lean using Media Bias/Fact Check data',
      'Equal sampling from left, center, and right-leaning sources',
      'International sources included for global perspective',
      'Breaking news prioritized within 4-hour windows',
    ],
  },
  {
    number: '02',
    icon: BeakerIcon,
    title: 'Topic Extraction',
    description:
      'AI algorithms identify trending topics and extract key themes, filtering out duplicates and low-relevance stories.',
    details: [
      'Natural Language Processing (NLP) for theme identification',
      'Cross-source validation to confirm story significance',
      'Deduplication to avoid repetitive polling',
      'Controversy scoring to identify high-interest topics',
    ],
  },
  {
    number: '03',
    icon: ScaleIcon,
    title: 'Question Generation',
    description:
      'Our AI generates poll questions designed to be neutral, clear, and capture the full range of public opinion.',
    details: [
      'Multiple AI models used with consensus voting',
      'Questions reviewed for leading language',
      'Answer options cover spectrum of reasonable positions',
      'Neutral framing guidelines enforced algorithmically',
    ],
  },
  {
    number: '04',
    icon: EyeIcon,
    title: 'Bias Review',
    description:
      'Each poll undergoes automated and manual review to detect and correct any unintentional bias.',
    details: [
      'Sentiment analysis on question wording',
      'Answer option balance verification',
      'Historical comparison with similar polls',
      'Community flagging for additional review',
    ],
  },
  {
    number: '05',
    icon: ShieldCheckIcon,
    title: 'Fraud Prevention',
    description:
      'Multi-layered verification ensures one-person-one-vote integrity without compromising privacy.',
    details: [
      'Email and phone verification options',
      'Device fingerprinting (privacy-preserving)',
      'Behavioral analysis for bot detection',
      'Rate limiting and CAPTCHA challenges',
    ],
  },
  {
    number: '06',
    icon: ChartBarIcon,
    title: 'Results Aggregation',
    description:
      'Votes are aggregated in real-time with demographic breakdowns available without individual identification.',
    details: [
      'Anonymous vote storage with cryptographic separation',
      'Real-time percentage calculations',
      'Demographic data aggregated at group level only',
      'Statistical confidence intervals provided',
    ],
  },
];

const principles = [
  {
    title: 'Neutrality',
    description:
      'Questions are worded to avoid favoring any particular answer. We never use loaded language, leading questions, or emotionally charged framing.',
  },
  {
    title: 'Transparency',
    description:
      'Every poll shows its source material, AI reasoning, and methodology. Users can understand exactly how each question was formulated.',
  },
  {
    title: 'Inclusivity',
    description:
      'Answer options are designed to capture the full spectrum of reasonable positions, including nuanced middle-ground options.',
  },
  {
    title: 'Privacy',
    description:
      'Individual votes are never linked to identities. Demographic data is only reported in aggregate to prevent re-identification.',
  },
];

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Section */}
      <div className="bg-linear-to-r from-primary-600 to-primary-700 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mx-auto h-16 w-16 rounded-full bg-white/20 flex items-center justify-center mb-6"
          >
            <SparklesIcon className="h-8 w-8 text-white" />
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl font-bold text-white sm:text-5xl"
          >
            Our Methodology
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-4 text-xl text-primary-100 max-w-3xl mx-auto"
          >
            How we create unbiased polls from current events using AI,
            rigorous standards, and transparent processes.
          </motion.p>
        </div>
      </div>

      {/* Core Principles */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              Core Principles
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              These foundational principles guide every aspect of our poll creation process.
            </p>
          </div>

          <div className="mt-12 grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {principles.map((principle, index) => (
              <motion.div
                key={principle.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                viewport={{ once: true }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {principle.title}
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-400">
                  {principle.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Process Steps */}
      <section className="py-16 sm:py-24 bg-white dark:bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              The TruePulse Process
            </h2>
            <p className="mt-4 text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              From news event to published poll, here&apos;s how we ensure quality and fairness.
            </p>
          </div>

          <div className="mt-16 space-y-16">
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: index % 2 === 0 ? -20 : 20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                className={`flex flex-col lg:flex-row items-start gap-8 ${
                  index % 2 === 1 ? 'lg:flex-row-reverse' : ''
                }`}
              >
                <div className="flex-1">
                  <div className="flex items-center gap-4 mb-4">
                    <span className="text-5xl font-bold text-primary-200 dark:text-primary-800">
                      {step.number}
                    </span>
                    <div className="h-12 w-12 rounded-lg bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <step.icon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-lg text-gray-600 dark:text-gray-400">
                    {step.description}
                  </p>
                </div>
                <div className="flex-1 w-full">
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-xl p-6">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-4">
                      Key Details
                    </h4>
                    <ul className="space-y-3">
                      {step.details.map((detail, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-primary-600 mt-1">•</span>
                          <span className="text-gray-600 dark:text-gray-400">
                            {detail}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* AI Model Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-2 lg:gap-16 items-center">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                AI-Powered, Human-Guided
              </h2>
              <p className="mt-4 text-lg text-gray-600 dark:text-gray-400">
                We use state-of-the-art language models to generate poll questions,
                but AI is just one part of our quality assurance process.
              </p>
              <div className="mt-8 space-y-6">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Multiple Model Consensus
                  </h3>
                  <p className="mt-1 text-gray-600 dark:text-gray-400">
                    Questions are generated by multiple AI models independently.
                    Only questions that achieve consensus on neutrality are published.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Bias Detection Algorithms
                  </h3>
                  <p className="mt-1 text-gray-600 dark:text-gray-400">
                    Specialized models analyze questions for sentiment imbalance,
                    loaded language, and structural bias.
                  </p>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Continuous Improvement
                  </h3>
                  <p className="mt-1 text-gray-600 dark:text-gray-400">
                    User feedback and expert review help us continuously refine
                    our algorithms and guidelines.
                  </p>
                </div>
              </div>
            </div>
            <div className="mt-12 lg:mt-0">
              <div className="bg-gray-900 rounded-2xl p-6 shadow-2xl">
                <div className="flex items-center gap-2 mb-4">
                  <div className="h-3 w-3 rounded-full bg-red-500" />
                  <div className="h-3 w-3 rounded-full bg-yellow-500" />
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="ml-2 text-sm text-gray-400">bias_check.py</span>
                </div>
                <pre className="text-sm text-gray-300 overflow-x-auto">
                  <code>{`def check_question_neutrality(question: str) -> Score:
    """
    Multi-model consensus check for bias.
    Returns neutrality score 0-100.
    """
    scores = []
    
    # Check sentiment balance
    sentiment = analyze_sentiment(question)
    scores.append(sentiment.neutrality)
    
    # Check for loaded language
    loaded = detect_loaded_words(question)
    scores.append(100 - loaded.severity)
    
    # Check answer option balance
    balance = check_option_balance(question)
    scores.append(balance.score)
    
    # Require consensus above threshold
    avg_score = sum(scores) / len(scores)
    
    if avg_score < NEUTRALITY_THRESHOLD:
        return Score(passed=False, value=avg_score)
    
    return Score(passed=True, value=avg_score)`}</code>
                </pre>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Transparency Section */}
      <section className="py-16 sm:py-24 bg-gray-900 text-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <DocumentTextIcon className="mx-auto h-12 w-12 text-primary-400" />
          <h2 className="mt-4 text-3xl font-bold">Full Transparency</h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            Every poll on TruePulse includes links to source articles, AI reasoning
            explanations, and methodology details. We believe you should be able to
            verify our work.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <a
              href="https://github.com/KevinRabun/TruePulse"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-gray-900 bg-white hover:bg-gray-100 transition-colors"
            >
              View Source Code
            </a>
            <Link
              href="/about"
              className="inline-flex items-center px-6 py-3 border border-white text-base font-medium rounded-lg text-white hover:bg-white/10 transition-colors"
            >
              Learn More About Us
            </Link>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 sm:py-24">
        <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white text-center">
            Frequently Asked Questions
          </h2>

          <div className="mt-12 space-y-8">
            {[
              {
                q: 'How do you ensure questions are truly unbiased?',
                a: 'We use multiple AI models that must reach consensus on neutrality, automated bias detection algorithms, and human review for edge cases. Questions that fail any check are revised or rejected.',
              },
              {
                q: 'What news sources do you use?',
                a: 'We aggregate from 200+ sources across the political spectrum, weighted equally between left-leaning, center, and right-leaning outlets as rated by independent media bias organizations.',
              },
              {
                q: 'How do you prevent vote manipulation?',
                a: 'Multi-factor verification, device fingerprinting, behavioral analysis, and rate limiting ensure one-person-one-vote integrity while preserving voter privacy.',
              },
              {
                q: 'Can I see the raw data?',
                a: 'Aggregated results are available under Creative Commons license. Raw vote data is never shared to protect individual privacy, but we publish statistical methodology reports.',
              },
              {
                q: 'How often are new polls generated?',
                a: 'New polls are generated hourly based on breaking news and trending topics. Each poll runs for a configurable duration (default: 1 hour) to capture timely public opinion.',
              },
            ].map((faq, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md"
              >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {faq.q}
                </h3>
                <p className="mt-2 text-gray-600 dark:text-gray-400">{faq.a}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 sm:py-24 bg-primary-600">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white">
            Ready to Participate?
          </h2>
          <p className="mt-4 text-lg text-primary-100 max-w-2xl mx-auto">
            Join thousands of users contributing to transparent, unbiased public opinion data.
          </p>
          <div className="mt-8">
            <Link
              href="/polls"
              className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg shadow-xs text-primary-600 bg-white hover:bg-gray-100 transition-colors"
            >
              Browse Current Polls
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
