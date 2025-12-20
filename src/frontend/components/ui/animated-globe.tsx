'use client';

import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

interface AnimatedGlobeProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  showActivity?: boolean;
  className?: string;
}

// Generate random points on a sphere for activity markers
function generateActivityPoints(count: number) {
  const points = [];
  for (let i = 0; i < count; i++) {
    // Random latitude/longitude converted to percentage position
    const lat = (Math.random() - 0.5) * 140; // -70 to 70 degrees
    const lng = (Math.random() - 0.5) * 360; // -180 to 180 degrees
    
    // Simple projection
    const x = 50 + (lng / 360) * 80;
    const y = 50 + (lat / 180) * 80;
    
    points.push({
      id: i,
      x: Math.max(15, Math.min(85, x)),
      y: Math.max(15, Math.min(85, y)),
      delay: Math.random() * 2,
      duration: 1 + Math.random() * 2,
    });
  }
  return points;
}

const sizes = {
  sm: 'w-16 h-16',
  md: 'w-24 h-24',
  lg: 'w-32 h-32',
  xl: 'w-48 h-48',
};

export function AnimatedGlobe({ size = 'lg', showActivity = true, className = '' }: AnimatedGlobeProps) {
  const [activityPoints, setActivityPoints] = useState<ReturnType<typeof generateActivityPoints>>([]);
  
  useEffect(() => {
    if (showActivity) {
      setActivityPoints(generateActivityPoints(8));
      
      // Regenerate points periodically
      const interval = setInterval(() => {
        setActivityPoints(generateActivityPoints(8));
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [showActivity]);

  return (
    <div className={`relative ${sizes[size]} ${className}`}>
      {/* Outer glow */}
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-primary-400/30 to-trust-400/30 blur-xl animate-pulse-slow" />
      
      {/* Main globe */}
      <motion.div
        className="relative w-full h-full rounded-full bg-gradient-to-br from-primary-500 via-primary-600 to-primary-700 shadow-lg overflow-hidden"
        animate={{ rotateY: 360 }}
        transition={{ duration: 30, repeat: Infinity, ease: 'linear' }}
      >
        {/* Globe grid lines */}
        <svg className="absolute inset-0 w-full h-full opacity-30" viewBox="0 0 100 100">
          {/* Latitude lines */}
          {[20, 35, 50, 65, 80].map((y) => (
            <ellipse
              key={`lat-${y}`}
              cx="50"
              cy={y}
              rx={40 * Math.cos(((y - 50) / 50) * Math.PI / 2)}
              ry="3"
              fill="none"
              stroke="white"
              strokeWidth="0.5"
            />
          ))}
          {/* Longitude lines */}
          {[0, 30, 60, 90, 120, 150].map((angle) => (
            <ellipse
              key={`lng-${angle}`}
              cx="50"
              cy="50"
              rx={Math.abs(40 * Math.cos((angle * Math.PI) / 180)) || 0.1}
              ry="40"
              fill="none"
              stroke="white"
              strokeWidth="0.5"
              transform={`rotate(${angle % 180 === 0 ? 0 : 90} 50 50)`}
            />
          ))}
        </svg>
        
        {/* Continent shapes (stylized) */}
        <svg className="absolute inset-0 w-full h-full opacity-50" viewBox="0 0 100 100">
          {/* North America */}
          <path
            d="M20,25 Q25,20 35,22 Q40,25 38,35 Q35,45 25,42 Q20,38 20,25"
            fill="rgba(255,255,255,0.4)"
          />
          {/* Europe */}
          <path
            d="M55,28 Q60,25 68,28 Q72,32 70,38 Q65,42 58,40 Q55,35 55,28"
            fill="rgba(255,255,255,0.4)"
          />
          {/* Asia */}
          <path
            d="M68,30 Q78,28 85,35 Q88,45 82,52 Q75,55 68,48 Q65,40 68,30"
            fill="rgba(255,255,255,0.4)"
          />
          {/* Africa */}
          <path
            d="M52,48 Q58,45 62,50 Q65,60 60,70 Q55,72 50,65 Q48,55 52,48"
            fill="rgba(255,255,255,0.4)"
          />
          {/* South America */}
          <path
            d="M30,55 Q35,52 38,58 Q40,68 35,75 Q28,78 26,68 Q25,60 30,55"
            fill="rgba(255,255,255,0.4)"
          />
          {/* Australia */}
          <path
            d="M78,62 Q85,60 88,65 Q88,72 82,74 Q76,73 76,68 Q76,64 78,62"
            fill="rgba(255,255,255,0.4)"
          />
        </svg>
        
        {/* Light reflection */}
        <div className="absolute top-2 left-2 w-1/4 h-1/4 rounded-full bg-white/30 blur-sm" />
      </motion.div>
      
      {/* Activity markers */}
      {showActivity && activityPoints.map((point) => (
        <motion.div
          key={point.id}
          className="absolute w-2 h-2"
          style={{ left: `${point.x}%`, top: `${point.y}%` }}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ 
            scale: [0, 1, 1, 0],
            opacity: [0, 1, 1, 0],
          }}
          transition={{
            duration: point.duration,
            delay: point.delay,
            repeat: Infinity,
            repeatDelay: 3,
          }}
        >
          {/* Ping effect */}
          <span className="absolute inset-0 rounded-full bg-trust-400 animate-ping" />
          <span className="absolute inset-0 rounded-full bg-trust-500" />
        </motion.div>
      ))}
      
      {/* Orbital ring */}
      <motion.div
        className="absolute -inset-4 border border-primary-300/30 rounded-full"
        style={{ 
          borderStyle: 'dashed',
          borderWidth: '1px',
        }}
        animate={{ rotate: -360 }}
        transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  );
}
