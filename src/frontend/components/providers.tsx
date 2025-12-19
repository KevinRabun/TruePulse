'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AuthProvider } from '@/lib/auth';
import { ToastProvider } from '@/components/ui/toast';
import { ThemeProvider } from '@/lib/theme';
import { AdProvider } from '@/components/ads';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 minute
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <AdProvider>
            <ToastProvider>
              {children}
            </ToastProvider>
          </AdProvider>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
