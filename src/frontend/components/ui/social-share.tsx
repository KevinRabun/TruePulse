'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Share2, X, Check, Link2, MessageCircle } from 'lucide-react';

// Social platform icons as simple SVG components
const TwitterIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
  </svg>
);

const FacebookIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
  </svg>
);

const LinkedInIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
  </svg>
);

const RedditIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701zM9.25 12C8.561 12 8 12.562 8 13.25c0 .687.561 1.248 1.25 1.248.687 0 1.248-.561 1.248-1.249 0-.688-.561-1.249-1.249-1.249zm5.5 0c-.687 0-1.248.561-1.248 1.25 0 .687.561 1.248 1.249 1.248.688 0 1.249-.561 1.249-1.249 0-.687-.562-1.249-1.25-1.249zm-5.466 3.99a.327.327 0 0 0-.231.094.33.33 0 0 0 0 .463c.842.842 2.484.913 2.961.913.477 0 2.105-.056 2.961-.913a.361.361 0 0 0 .029-.463.33.33 0 0 0-.464 0c-.547.533-1.684.73-2.512.73-.828 0-1.979-.196-2.512-.73a.326.326 0 0 0-.232-.095z" />
  </svg>
);

const WhatsAppIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
  </svg>
);

const TelegramIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z" />
  </svg>
);

export interface ShareContent {
  title: string;
  text?: string;
  url: string;
  hashtags?: string[];
  pollId?: string; // Optional poll ID for tracking share achievements
}

interface SocialShareProps {
  content: ShareContent;
  variant?: 'button' | 'icon';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  onShareTracked?: (result: ShareTrackResult) => void; // Callback for share tracking
}

interface ShareTrackResult {
  points_earned: number;
  total_shares: number;
  new_achievements: Array<{
    id: string;
    name: string;
    description: string;
    icon: string;
    points_reward: number;
  }>;
  message: string;
}

// Track a share action with the backend
async function trackShare(pollId: string, platform: string): Promise<ShareTrackResult | null> {
  try {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) return null;
    
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/gamification/share`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({
        poll_id: pollId,
        platform: platform,
      }),
    });
    
    if (response.ok) {
      return await response.json();
    }
    return null;
  } catch (err) {
    console.error('Failed to track share:', err);
    return null;
  }
}

const platforms = [
  {
    name: 'X (Twitter)',
    icon: TwitterIcon,
    color: 'hover:bg-black hover:text-white',
    getUrl: (content: ShareContent) => {
      const params = new URLSearchParams({
        text: content.text || content.title,
        url: content.url,
        ...(content.hashtags?.length && { hashtags: content.hashtags.join(',') }),
      });
      return `https://twitter.com/intent/tweet?${params}`;
    },
  },
  {
    name: 'Facebook',
    icon: FacebookIcon,
    color: 'hover:bg-[#1877F2] hover:text-white',
    getUrl: (content: ShareContent) => {
      const params = new URLSearchParams({ u: content.url });
      return `https://www.facebook.com/sharer/sharer.php?${params}`;
    },
  },
  {
    name: 'LinkedIn',
    icon: LinkedInIcon,
    color: 'hover:bg-[#0A66C2] hover:text-white',
    getUrl: (content: ShareContent) => {
      const params = new URLSearchParams({
        url: content.url,
        title: content.title,
        ...(content.text && { summary: content.text }),
      });
      return `https://www.linkedin.com/sharing/share-offsite/?${params}`;
    },
  },
  {
    name: 'Reddit',
    icon: RedditIcon,
    color: 'hover:bg-[#FF4500] hover:text-white',
    getUrl: (content: ShareContent) => {
      const params = new URLSearchParams({
        url: content.url,
        title: content.title,
      });
      return `https://www.reddit.com/submit?${params}`;
    },
  },
  {
    name: 'WhatsApp',
    icon: WhatsAppIcon,
    color: 'hover:bg-[#25D366] hover:text-white',
    getUrl: (content: ShareContent) => {
      const text = `${content.text || content.title} ${content.url}`;
      return `https://wa.me/?text=${encodeURIComponent(text)}`;
    },
  },
  {
    name: 'Telegram',
    icon: TelegramIcon,
    color: 'hover:bg-[#0088cc] hover:text-white',
    getUrl: (content: ShareContent) => {
      const params = new URLSearchParams({
        url: content.url,
        text: content.text || content.title,
      });
      return `https://t.me/share/url?${params}`;
    },
  },
];

export function SocialShare({ content, variant = 'button', size = 'md', className = '', onShareTracked }: SocialShareProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Calculate dropdown position when opening
  const updatePosition = useCallback(() => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      const dropdownWidth = 224; // w-56 = 14rem = 224px
      const dropdownHeight = 400; // approximate max height
      const padding = 8;
      
      let top = rect.bottom + padding;
      let left = rect.right - dropdownWidth;
      
      // Ensure dropdown doesn't go off-screen on the right
      if (left < padding) {
        left = padding;
      }
      
      // Ensure dropdown doesn't go off-screen at the bottom
      if (top + dropdownHeight > window.innerHeight - padding) {
        top = rect.top - dropdownHeight - padding;
      }
      
      setDropdownPosition({ top, left });
    }
  }, []);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current && 
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Update position on scroll/resize when open
  useEffect(() => {
    if (isOpen) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isOpen, updatePosition]);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(content.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      
      // Track the share if we have a pollId
      if (content.pollId) {
        const result = await trackShare(content.pollId, 'copy');
        if (result && onShareTracked) {
          onShareTracked(result);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: content.title,
          text: content.text,
          url: content.url,
        });
        setIsOpen(false);
        
        // Track the share if we have a pollId
        if (content.pollId) {
          const result = await trackShare(content.pollId, 'native');
          if (result && onShareTracked) {
            onShareTracked(result);
          }
        }
      } catch (err) {
        // User cancelled or share failed
        if ((err as Error).name !== 'AbortError') {
          console.error('Share failed:', err);
        }
      }
    }
  };

  const handlePlatformClick = async (url: string, platformName: string) => {
    window.open(url, '_blank', 'noopener,noreferrer,width=600,height=400');
    setIsOpen(false);
    
    // Track the share if we have a pollId
    if (content.pollId) {
      // Map platform display name to backend platform key
      const platformMap: Record<string, string> = {
        'X (Twitter)': 'twitter',
        'Facebook': 'facebook',
        'LinkedIn': 'linkedin',
        'Reddit': 'reddit',
        'WhatsApp': 'whatsapp',
        'Telegram': 'telegram',
      };
      const platform = platformMap[platformName] || platformName.toLowerCase();
      const result = await trackShare(content.pollId, platform);
      if (result && onShareTracked) {
        onShareTracked(result);
      }
    }
  };

  const sizeClasses = {
    sm: 'p-1.5',
    md: 'p-2',
    lg: 'p-2.5',
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  return (
    <div className={`relative ${className}`}>
      {/* Trigger Button */}
      <motion.button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          ${sizeClasses[size]}
          rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-white
          hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
          ${variant === 'button' ? 'flex items-center gap-2 px-3' : ''}
        `}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label="Share"
      >
        <Share2 className={iconSizes[size]} />
        {variant === 'button' && <span className="text-sm font-medium">Share</span>}
      </motion.button>

      {/* Dropdown Menu - Rendered in Portal */}
      {typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          {isOpen && (
            <motion.div
              ref={menuRef}
              initial={{ opacity: 0, scale: 0.95, y: -10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -10 }}
              transition={{ duration: 0.15 }}
              style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
              className="fixed w-56 rounded-xl bg-white dark:bg-gray-800 shadow-xl ring-1 ring-black/5 dark:ring-white/10 py-2 z-[9999] overflow-hidden"
            >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-700">
              <span className="text-sm font-medium text-gray-900 dark:text-white">Share</span>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Native Share (if available) */}
            {typeof navigator !== 'undefined' && 'share' in navigator && (
              <button
                onClick={handleNativeShare}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400">
                  <MessageCircle className="h-4 w-4" />
                </div>
                <span>More options...</span>
              </button>
            )}

            {/* Social Platforms */}
            <div className="py-1">
              {platforms.map((platform) => (
                <button
                  key={platform.name}
                  onClick={() => handlePlatformClick(platform.getUrl(content), platform.name)}
                  className={`flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 transition-colors ${platform.color}`}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700">
                    <platform.icon className="h-4 w-4" />
                  </div>
                  <span>{platform.name}</span>
                </button>
              ))}
            </div>

            {/* Copy Link */}
            <div className="border-t border-gray-100 dark:border-gray-700 pt-1">
              <button
                onClick={handleCopyLink}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
                  copied 
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' 
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                }`}>
                  {copied ? <Check className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
                </div>
                <span>{copied ? 'Copied!' : 'Copy link'}</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>,
      document.body
      )}
    </div>
  );
}

// Compact inline share buttons for achievement cards
export function ShareButtons({ content, className = '', onShareTracked }: { content: ShareContent; className?: string; onShareTracked?: (result: ShareTrackResult) => void }) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(content.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      
      // Track the share if we have a pollId
      if (content.pollId) {
        const result = await trackShare(content.pollId, 'copy');
        if (result && onShareTracked) {
          onShareTracked(result);
        }
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async (url: string, platformName: string) => {
    window.open(url, '_blank', 'noopener,noreferrer,width=600,height=400');
    
    // Track the share if we have a pollId
    if (content.pollId) {
      const platformMap: Record<string, string> = {
        'X (Twitter)': 'twitter',
        'Facebook': 'facebook',
        'LinkedIn': 'linkedin',
        'Reddit': 'reddit',
        'WhatsApp': 'whatsapp',
        'Telegram': 'telegram',
      };
      const platform = platformMap[platformName] || platformName.toLowerCase();
      const result = await trackShare(content.pollId, platform);
      if (result && onShareTracked) {
        onShareTracked(result);
      }
    }
  };

  const quickPlatforms = platforms.slice(0, 3); // X, Facebook, LinkedIn

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {quickPlatforms.map((platform) => (
        <motion.button
          key={platform.name}
          onClick={() => handleShare(platform.getUrl(content), platform.name)}
          className="p-1.5 rounded-md text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          title={`Share on ${platform.name}`}
        >
          <platform.icon className="h-4 w-4" />
        </motion.button>
      ))}
      <motion.button
        onClick={handleCopyLink}
        className={`p-1.5 rounded-md transition-colors ${
          copied 
            ? 'text-green-500 bg-green-50 dark:bg-green-900/30' 
            : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
        }`}
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        title={copied ? 'Copied!' : 'Copy link'}
      >
        {copied ? <Check className="h-4 w-4" /> : <Link2 className="h-4 w-4" />}
      </motion.button>
    </div>
  );
}
