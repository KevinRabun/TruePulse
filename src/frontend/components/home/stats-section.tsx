'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { Globe2, Users, BarChart3, Vote, MapPin } from 'lucide-react';

interface StatItem {
  label: string;
  value: string;
  suffix: string;
  icon: typeof Globe2;
  color: string;
}

// Default/fallback stats while loading or on error
const defaultStats: StatItem[] = [
  { label: 'Countries Represented', value: '—', suffix: '', icon: Globe2, color: 'from-primary-400 to-trust-400' },
  { label: 'Polls Created', value: '—', suffix: '', icon: BarChart3, color: 'from-primary-400 to-primary-600' },
  { label: 'Votes Cast', value: '—', suffix: '', icon: Vote, color: 'from-accent-400 to-accent-600' },
  { label: 'Active Community', value: '—', suffix: '', icon: Users, color: 'from-warm-400 to-warm-600' },
];

export function StatsSection() {
  const [stats, setStats] = useState<StatItem[]>(defaultStats);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await api.getPlatformStats();
        const { stats: platformStats } = response;
        
        setStats([
          { 
            label: 'Countries Represented', 
            value: platformStats.countries_represented_raw > 0 ? String(platformStats.countries_represented_raw) : '—', 
            suffix: platformStats.countries_represented_raw > 0 ? '' : '',
            icon: Globe2,
            color: 'from-primary-400 to-trust-400'
          },
          { 
            label: 'Polls Created', 
            value: platformStats.polls_created, 
            suffix: '+',
            icon: BarChart3,
            color: 'from-primary-400 to-primary-600'
          },
          { 
            label: 'Votes Cast', 
            value: platformStats.votes_cast, 
            suffix: '+',
            icon: Vote,
            color: 'from-accent-400 to-accent-600'
          },
          { 
            label: 'Active Community', 
            value: platformStats.active_users, 
            suffix: '',
            icon: Users,
            color: 'from-warm-400 to-warm-600'
          },
        ]);
      } catch (error) {
        console.error('Failed to fetch platform stats:', error);
        // Keep showing default placeholder stats on error
      } finally {
        setIsLoading(false);
      }
    }

    fetchStats();
  }, []);

  return (
    <section className="relative py-20 overflow-hidden">
      {/* Background with globe pattern */}
      <div className="absolute inset-0 bg-linear-to-br from-gray-900 via-primary-950 to-gray-900" />
      <div className="absolute inset-0 opacity-10" style={{
        backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.15) 1px, transparent 0)`,
        backgroundSize: '40px 40px'
      }} />
      
      {/* Animated accent orbs */}
      <motion.div
        className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary-500/20 rounded-full blur-3xl"
        animate={{ scale: [1, 1.2, 1], opacity: [0.2, 0.3, 0.2] }}
        transition={{ duration: 8, repeat: Infinity }}
      />
      <motion.div
        className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent-500/20 rounded-full blur-3xl"
        animate={{ scale: [1.2, 1, 1.2], opacity: [0.2, 0.3, 0.2] }}
        transition={{ duration: 8, repeat: Infinity, delay: 4 }}
      />
      
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section header */}
        <motion.div 
          className="text-center mb-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl font-bold text-white sm:text-4xl">
            A Truly <span className="bg-linear-to-r from-primary-400 to-trust-400 bg-clip-text text-transparent">Global</span> Community
          </h2>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            Voices from every corner of the world, united in shaping the conversation that matters.
          </p>
        </motion.div>
        
        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="relative group"
            >
              <div className="relative bg-white/5 backdrop-blur-xs rounded-2xl p-6 border border-white/10 hover:border-white/20 transition-all hover:bg-white/10">
                {/* Icon */}
                <div className={`inline-flex p-3 rounded-xl bg-linear-to-br ${stat.color} shadow-lg mb-4`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                
                {/* Value */}
                <div className={`text-3xl lg:text-4xl font-bold text-white ${isLoading ? 'animate-pulse' : ''}`}>
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    key={stat.value}
                  >
                    {stat.value}
                  </motion.span>
                  <span className={`bg-linear-to-r ${stat.color} bg-clip-text text-transparent`}>{stat.suffix}</span>
                </div>
                
                {/* Label */}
                <div className="mt-2 text-sm text-gray-400 font-medium">{stat.label}</div>
                
                {/* Live indicator for active users */}
                {stat.label === 'Active Community' && (
                  <div className="absolute top-4 right-4">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-trust-400 opacity-75" />
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-trust-500" />
                    </span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
        
        {/* Global regions indicator */}
        <motion.div 
          className="mt-12 flex flex-wrap justify-center gap-3"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          viewport={{ once: true }}
        >
          {['North America', 'Europe', 'Asia', 'Africa', 'South America', 'Oceania'].map((region, i) => (
            <motion.span
              key={region}
              className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-gray-400"
              initial={{ opacity: 0, x: -10 }}
              whileInView={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 + i * 0.05 }}
              viewport={{ once: true }}
            >
              <MapPin className="h-3 w-3 text-primary-400" />
              {region}
            </motion.span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
