'use client';

import { useTheme } from '@/lib/theme';
import { SunIcon, MoonIcon, ComputerDesktopIcon, CheckIcon } from '@heroicons/react/24/outline';
import { motion } from 'framer-motion';

const themeOptions = [
  {
    value: 'light' as const,
    label: 'Light',
    description: 'Always use light theme',
    icon: SunIcon,
  },
  {
    value: 'dark' as const,
    label: 'Dark',
    description: 'Always use dark theme',
    icon: MoonIcon,
  },
  {
    value: 'system' as const,
    label: 'System',
    description: 'Match your device settings',
    icon: ComputerDesktopIcon,
  },
];

interface ThemeSettingsProps {
  onUpdate?: () => void;
}

export function ThemeSettings({ onUpdate }: ThemeSettingsProps) {
  const { theme, setTheme, isLoading } = useTheme();

  const handleThemeChange = (newTheme: 'light' | 'dark' | 'system') => {
    setTheme(newTheme);
    onUpdate?.();
  };

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-primary-500/20 rounded-lg">
          <SunIcon className="h-6 w-6 text-primary-500 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Appearance</h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">Choose your preferred theme</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {themeOptions.map((option) => {
          const isSelected = theme === option.value;
          const Icon = option.icon;
          
          return (
            <motion.button
              key={option.value}
              onClick={() => handleThemeChange(option.value)}
              disabled={isLoading}
              className={`
                relative flex flex-col items-center p-4 rounded-xl border-2 transition-all
                ${isSelected
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500 hover:bg-gray-50 dark:hover:bg-slate-700/50'
                }
                ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              `}
              whileHover={!isLoading ? { scale: 1.02 } : {}}
              whileTap={!isLoading ? { scale: 0.98 } : {}}
            >
              {/* Selected indicator */}
              {isSelected && (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="absolute top-2 right-2 p-0.5 bg-primary-500 rounded-full"
                >
                  <CheckIcon className="h-3 w-3 text-white" />
                </motion.div>
              )}
              
              {/* Icon */}
              <div className={`
                p-3 rounded-xl mb-3
                ${isSelected
                  ? 'bg-primary-100 dark:bg-primary-800/30'
                  : 'bg-gray-100 dark:bg-slate-700'
                }
              `}>
                <Icon className={`
                  h-6 w-6
                  ${isSelected
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-500 dark:text-slate-400'
                  }
                `} />
              </div>
              
              {/* Label */}
              <span className={`
                font-medium text-sm
                ${isSelected
                  ? 'text-primary-700 dark:text-primary-300'
                  : 'text-gray-700 dark:text-slate-300'
                }
              `}>
                {option.label}
              </span>
              
              {/* Description */}
              <span className="text-xs text-gray-500 dark:text-slate-500 mt-1 text-center">
                {option.description}
              </span>
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
