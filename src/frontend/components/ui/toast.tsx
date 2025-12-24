'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface ToastContextType {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
  info: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

const toastIcons: Record<ToastType, typeof CheckCircleIcon> = {
  success: CheckCircleIcon,
  error: ExclamationCircleIcon,
  info: InformationCircleIcon,
  warning: ExclamationCircleIcon,
};

const toastStyles: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: {
    bg: 'bg-green-900/95',
    border: 'border-green-500/50',
    icon: 'text-green-400',
  },
  error: {
    bg: 'bg-red-900/95',
    border: 'border-red-500/50',
    icon: 'text-red-400',
  },
  info: {
    bg: 'bg-blue-900/95',
    border: 'border-blue-500/50',
    icon: 'text-blue-400',
  },
  warning: {
    bg: 'bg-yellow-900/95',
    border: 'border-yellow-500/50',
    icon: 'text-yellow-400',
  },
};

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: () => void }) {
  const Icon = toastIcons[toast.type];
  const styles = toastStyles[toast.type];

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`${styles.bg} ${styles.border} border rounded-xl p-4 shadow-lg backdrop-blur-xs min-w-75 max-w-100`}
    >
      <div className="flex items-start gap-3">
        <Icon className={`h-5 w-5 ${styles.icon} shrink-0 mt-0.5`} />
        <div className="flex-1 min-w-0">
          <p className="text-white font-medium">{toast.title}</p>
          {toast.message && (
            <p className="text-slate-400 text-sm mt-1">{toast.message}</p>
          )}
        </div>
        <button
          onClick={onRemove}
          className="text-slate-400 hover:text-white transition-colors shrink-0"
        >
          <XMarkIcon className="h-5 w-5" />
        </button>
      </div>
    </motion.div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback(
    (toast: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast = { ...toast, id };
      setToasts((prev) => [...prev, newToast]);

      // Auto-remove after duration (default 5 seconds)
      const duration = toast.duration ?? 5000;
      setTimeout(() => {
        removeToast(id);
      }, duration);
    },
    [removeToast]
  );

  const success = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'success', title, message });
    },
    [addToast]
  );

  const error = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'error', title, message, duration: 7000 });
    },
    [addToast]
  );

  const info = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'info', title, message });
    },
    [addToast]
  );

  const warning = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'warning', title, message, duration: 6000 });
    },
    [addToast]
  );

  return (
    <ToastContext.Provider
      value={{ toasts, addToast, removeToast, success, error, info, warning }}
    >
      {children}
      {/* Toast Container */}
      <div className="fixed top-4 right-4 z-100 flex flex-col gap-2">
        <AnimatePresence mode="sync">
          {toasts.map((toast) => (
            <ToastItem
              key={toast.id}
              toast={toast}
              onRemove={() => removeToast(toast.id)}
            />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
