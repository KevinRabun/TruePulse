import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
import './globals.css';
import { Providers } from '@/components/providers';
import { Header } from '@/components/layout/header';
import { Footer } from '@/components/layout/footer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'TruePulse - Unbiased Public Opinion',
  description: 'Privacy-first polling platform with AI-powered unbiased poll generation from current events.',
  keywords: ['polls', 'voting', 'public opinion', 'democracy', 'unbiased'],
  authors: [{ name: 'TruePulse' }],
  openGraph: {
    title: 'TruePulse - Unbiased Public Opinion',
    description: 'Privacy-first polling platform with AI-powered unbiased poll generation.',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full" suppressHydrationWarning>
      <head>
        <meta name="google-adsense-account" content="ca-pub-6058579257544032" />
        <Script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-6058579257544032"
          crossOrigin="anonymous"
          strategy="afterInteractive"
        />
      </head>
      <body className={`${inter.className} h-full bg-gray-50 dark:bg-slate-900`}>
        <Providers>
          <div className="flex min-h-full flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}
