'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useState, useCallback } from 'react';

interface ConfettiPiece {
  id: number;
  x: number;
  color: string;
  delay: number;
  rotation: number;
  scale: number;
}

interface CelebrationProps {
  trigger: boolean;
  variant?: 'confetti' | 'stars' | 'sparkles';
  duration?: number;
  onComplete?: () => void;
}

const colors = [
  '#0ea5e9', // primary blue
  '#22c55e', // trust green
  '#f97316', // warm orange
  '#d946ef', // accent purple
  '#facc15', // gold
  '#ec4899', // pink
];

export function Celebration({ trigger, variant = 'confetti', duration = 3000, onComplete }: CelebrationProps) {
  const [pieces, setPieces] = useState<ConfettiPiece[]>([]);
  const [isActive, setIsActive] = useState(false);

  const generatePieces = useCallback(() => {
    const newPieces: ConfettiPiece[] = [];
    const count = variant === 'stars' ? 20 : 40;
    
    for (let i = 0; i < count; i++) {
      newPieces.push({
        id: i,
        x: Math.random() * 100,
        color: colors[Math.floor(Math.random() * colors.length)],
        delay: Math.random() * 0.5,
        rotation: Math.random() * 360,
        scale: 0.5 + Math.random() * 1,
      });
    }
    return newPieces;
  }, [variant]);

  useEffect(() => {
    if (trigger && !isActive) {
      setIsActive(true);
      setPieces(generatePieces());
      
      const timer = setTimeout(() => {
        setIsActive(false);
        setPieces([]);
        onComplete?.();
      }, duration);
      
      return () => clearTimeout(timer);
    }
  }, [trigger, duration, onComplete, generatePieces, isActive]);

  const renderPiece = (piece: ConfettiPiece) => {
    if (variant === 'stars') {
      return (
        <motion.div
          key={piece.id}
          className="absolute"
          style={{ left: `${piece.x}%`, bottom: '0%' }}
          initial={{ y: 0, opacity: 1, rotate: 0 }}
          animate={{
            y: -window.innerHeight * (0.5 + Math.random() * 0.5),
            opacity: [1, 1, 0],
            rotate: piece.rotation + 360,
            scale: [piece.scale, piece.scale * 1.5, 0],
          }}
          transition={{
            duration: 2 + Math.random(),
            delay: piece.delay,
            ease: 'easeOut',
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill={piece.color}>
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
          </svg>
        </motion.div>
      );
    }
    
    if (variant === 'sparkles') {
      return (
        <motion.div
          key={piece.id}
          className="absolute"
          style={{ left: `${piece.x}%`, top: '50%' }}
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            scale: [0, piece.scale, 0],
            opacity: [0, 1, 0],
            x: (Math.random() - 0.5) * 200,
            y: (Math.random() - 0.5) * 200,
          }}
          transition={{
            duration: 1 + Math.random(),
            delay: piece.delay,
            ease: 'easeOut',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill={piece.color}>
            <path d="M12 0L14.59 9.41L24 12L14.59 14.59L12 24L9.41 14.59L0 12L9.41 9.41L12 0Z" />
          </svg>
        </motion.div>
      );
    }

    // Default confetti
    return (
      <motion.div
        key={piece.id}
        className="absolute w-3 h-3"
        style={{ 
          left: `${piece.x}%`, 
          bottom: '0%',
          backgroundColor: piece.color,
          borderRadius: Math.random() > 0.5 ? '50%' : '2px',
        }}
        initial={{ y: 0, opacity: 1, rotate: 0 }}
        animate={{
          y: -window.innerHeight * (0.3 + Math.random() * 0.5),
          opacity: [1, 1, 0],
          rotate: piece.rotation + (Math.random() > 0.5 ? 360 : -360) * 2,
          x: (Math.random() - 0.5) * 200,
        }}
        transition={{
          duration: 2 + Math.random(),
          delay: piece.delay,
          ease: [0.25, 0.46, 0.45, 0.94],
        }}
      />
    );
  };

  return (
    <AnimatePresence>
      {isActive && (
        <div className="fixed inset-0 pointer-events-none z-50 overflow-hidden">
          {pieces.map(renderPiece)}
        </div>
      )}
    </AnimatePresence>
  );
}

// Points animation that floats up
interface PointsPopupProps {
  points: number;
  trigger: boolean;
  onComplete?: () => void;
}

export function PointsPopup({ points, trigger, onComplete }: PointsPopupProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (trigger) {
      setIsVisible(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        onComplete?.();
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [trigger, onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          className="fixed top-1/2 left-1/2 z-50 pointer-events-none"
          initial={{ x: '-50%', y: '-50%', scale: 0, opacity: 0 }}
          animate={{ 
            x: '-50%', 
            y: ['-50%', '-150%'],
            scale: [0, 1.5, 1.2],
            opacity: [0, 1, 0],
          }}
          exit={{ opacity: 0 }}
          transition={{ duration: 2, ease: 'easeOut' }}
        >
          <div className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-primary-500 to-accent-500 rounded-full shadow-lg">
            <span className="text-2xl font-bold text-white">+{points}</span>
            <span className="text-lg text-white/90">points!</span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// Achievement unlock animation
interface AchievementUnlockProps {
  title: string;
  description: string;
  tier: string;
  trigger: boolean;
  onComplete?: () => void;
}

export function AchievementUnlock({ title, description, tier, trigger, onComplete }: AchievementUnlockProps) {
  const [isVisible, setIsVisible] = useState(false);

  const tierColors: Record<string, string> = {
    bronze: 'from-amber-500 to-amber-700',
    silver: 'from-slate-300 to-slate-500',
    gold: 'from-yellow-400 to-yellow-600',
    platinum: 'from-purple-400 to-cyan-400',
  };

  useEffect(() => {
    if (trigger) {
      setIsVisible(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        onComplete?.();
      }, 4000);
      return () => clearTimeout(timer);
    }
  }, [trigger, onComplete]);

  return (
    <AnimatePresence>
      {isVisible && (
        <>
          <Celebration trigger={true} variant="stars" />
          <motion.div
            className="fixed top-20 left-1/2 z-50"
            initial={{ x: '-50%', y: -100, opacity: 0 }}
            animate={{ x: '-50%', y: 0, opacity: 1 }}
            exit={{ x: '-50%', y: -100, opacity: 0 }}
            transition={{ type: 'spring', damping: 15 }}
          >
            <div className={`relative px-8 py-4 rounded-xl shadow-2xl bg-gradient-to-r ${tierColors[tier] || tierColors.bronze}`}>
              {/* Glow effect */}
              <div className="absolute inset-0 rounded-xl bg-white/20 animate-pulse" />
              
              <div className="relative text-center">
                <motion.div
                  initial={{ scale: 0, rotate: -180 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ delay: 0.2, type: 'spring', damping: 10 }}
                  className="text-4xl mb-2"
                >
                  🏆
                </motion.div>
                <p className="text-xs uppercase tracking-wider text-white/80 font-semibold">
                  Achievement Unlocked!
                </p>
                <h3 className="text-xl font-bold text-white mt-1">{title}</h3>
                <p className="text-sm text-white/90 mt-1">{description}</p>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
