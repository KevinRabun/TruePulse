'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { BarChart3, Shield, Zap, Globe, Users, CheckCircle } from 'lucide-react';
import { AnimatedGlobe } from '@/components/ui/animated-globe';
import { FloatingActivityBadge } from '@/components/ui/live-activity';
import { TrustBadge } from '@/components/ui/trust-badge';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
};

interface HeroStats {
  countries: string;
  votesCast: string;
  completedPolls: string;
}

export function HeroSection() {
  const { isAuthenticated } = useAuth();
  const [stats, setStats] = useState<HeroStats>({
    countries: '150+',
    votesCast: '---',
    completedPolls: '---',
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await api.getPlatformStats();
        const countriesCount = response.stats.countries_represented_raw;
        setStats({
          countries: countriesCount > 0 ? `${countriesCount}` : '---',
          votesCast: response.stats.votes_cast,
          completedPolls: response.stats.completed_polls,
        });
      } catch (error) {
        console.error('Failed to fetch platform stats:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStats();
  }, []);
  return (
    <section className="relative bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0">
        {/* Grid pattern */}
        <div className="absolute inset-0 bg-grid-white/[0.03] bg-[size:60px_60px]" />
        
        {/* Floating orbs for depth */}
        <motion.div
          className="absolute top-20 left-10 w-64 h-64 bg-accent-500/20 rounded-full blur-3xl"
          animate={{ 
            x: [0, 30, 0],
            y: [0, -20, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="absolute bottom-20 right-10 w-96 h-96 bg-trust-500/10 rounded-full blur-3xl"
          animate={{ 
            x: [0, -20, 0],
            y: [0, 30, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>
      
      <div className="relative mx-auto max-w-7xl px-4 py-20 sm:px-6 lg:px-8 lg:py-28">
        <div className="lg:grid lg:grid-cols-2 lg:gap-12 items-center">
          {/* Left content */}
          <motion.div 
            className="text-center lg:text-left"
            variants={staggerContainer}
            initial="initial"
            animate="animate"
          >
            {/* Trust indicators */}
            <motion.div 
              variants={fadeInUp}
              className="flex flex-wrap gap-2 justify-center lg:justify-start mb-6"
            >
              <TrustBadge variant="secure" size="sm" />
              <TrustBadge variant="anonymous" size="sm" />
            </motion.div>
            
            <motion.h1 
              variants={fadeInUp}
              className="text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl"
            >
              The World&apos;s Voice.{' '}
              <span className="bg-gradient-to-r from-trust-300 to-primary-200 bg-clip-text text-transparent">
                United.
              </span>
            </motion.h1>
            
            <motion.p 
              variants={fadeInUp}
              className="mx-auto lg:mx-0 mt-6 max-w-xl text-xl text-primary-100"
            >
              Join millions in shaping the global conversation. AI-powered, privacy-first polling that captures what humanity really thinks.
            </motion.p>
            
            {/* Live activity badge */}
            <motion.div 
              variants={fadeInUp}
              className="mt-6 flex justify-center lg:justify-start"
            >
              <FloatingActivityBadge />
            </motion.div>
            
            <motion.div 
              variants={fadeInUp}
              className="mt-8 flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4"
            >
              <Link
                href={isAuthenticated ? "/polls" : "/register"}
                className="group relative inline-flex items-center gap-2 rounded-xl bg-white px-8 py-4 text-lg font-semibold text-primary-600 shadow-lg hover:shadow-xl hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-primary-600 transition-all duration-300"
              >
                <span>{isAuthenticated ? "Vote Now" : "Add Your Voice"}</span>
                <motion.span
                  className="inline-block"
                  animate={{ x: [0, 4, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  →
                </motion.span>
                {/* Shimmer effect */}
                <div className="absolute inset-0 rounded-xl overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent translate-x-[-200%] group-hover:translate-x-[200%] transition-transform duration-1000" />
                </div>
              </Link>
              <Link
                href="/polls"
                className="flex items-center gap-2 text-lg font-semibold text-white hover:text-primary-100 transition-colors"
              >
                <Globe className="h-5 w-5" />
                <span>Explore Polls</span>
              </Link>
            </motion.div>
            
            {/* Social proof stats */}
            <motion.div 
              variants={fadeInUp}
              className="mt-10 grid grid-cols-3 gap-4 max-w-md mx-auto lg:mx-0"
            >
              {[
                { value: stats.countries, label: 'Countries' },
                { value: stats.votesCast, label: 'Votes Cast' },
                { value: stats.completedPolls, label: 'Polls Completed' },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className={`text-2xl font-bold text-white ${isLoading ? 'animate-pulse' : ''}`}>
                    {stat.value}
                  </div>
                  <div className="text-sm text-primary-200">{stat.label}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>
          
          {/* Right side - Globe visualization */}
          <motion.div 
            className="hidden lg:flex items-center justify-center mt-12 lg:mt-0"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="relative">
              <AnimatedGlobe size="xl" showActivity={true} />
              
              {/* Floating feature cards around globe */}
              <motion.div
                className="absolute -top-4 -right-8 bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-lg px-4 py-2 shadow-lg"
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-trust-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Anonymous</span>
                </div>
              </motion.div>
              
              <motion.div
                className="absolute -bottom-4 -left-8 bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-lg px-4 py-2 shadow-lg"
                animate={{ y: [0, 8, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
              >
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">Global Community</span>
                </div>
              </motion.div>
              
              <motion.div
                className="absolute top-1/2 -right-16 bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm rounded-lg px-4 py-2 shadow-lg"
                animate={{ x: [0, 5, 0] }}
                transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
              >
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-warm-500" />
                  <span className="text-sm font-medium text-gray-900 dark:text-white">AI-Verified</span>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </div>
        
        {/* Feature highlights - mobile & desktop */}
        <motion.div 
          className="mt-20 grid grid-cols-1 gap-6 sm:grid-cols-3"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          {[
            {
              icon: BarChart3,
              title: 'AI-Generated Polls',
              description: 'Unbiased questions from multiple news sources worldwide',
              color: 'from-primary-400 to-primary-600',
            },
            {
              icon: Shield,
              title: 'Privacy Protected',
              description: 'Your votes are encrypted and can never be traced back to you',
              color: 'from-trust-400 to-trust-600',
            },
            {
              icon: Zap,
              title: 'Earn Rewards',
              description: 'Collect points, unlock achievements, and climb the leaderboard',
              color: 'from-warm-400 to-warm-600',
            },
          ].map((feature, index) => (
            <motion.div
              key={feature.title}
              className="group relative bg-white/10 backdrop-blur-sm rounded-2xl p-6 hover:bg-white/15 transition-all duration-300"
              whileHover={{ y: -4, scale: 1.02 }}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 + index * 0.1 }}
            >
              <div className={`inline-flex rounded-xl bg-gradient-to-br ${feature.color} p-3 shadow-lg`}>
                <feature.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-white">{feature.title}</h3>
              <p className="mt-2 text-sm text-primary-100">{feature.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
