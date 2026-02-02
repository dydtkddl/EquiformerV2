import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'SurfScreen Dashboard',
  description: 'Enterprise Surface Adsorption Screening Platform',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" className="dark">
      <head>
        <style>{`
          :root {
            --toast-bg: #1f2937;
            --toast-color: #f3f4f6;
          }
          .light {
            --toast-bg: #ffffff;
            --toast-color: #111827;
          }
        `}</style>
      </head>
      <body className={inter.className}>
        {children}
      </body>
    </html>
  );
}
