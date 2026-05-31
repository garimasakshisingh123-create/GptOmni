// app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'GptOmni — Grounded, Verifiable AI Assistant',
  description: 'ChatGPT-style AI assistant with a 9-stage verification pipeline. Every claim is fact-checked, every source is cited, every step is auditable.',
  keywords: ['AI assistant', 'fact-checking', 'RAG', 'verified AI', 'GptOmni'],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-[#212121] text-[#ececec]`}>
        {children}
      </body>
    </html>
  );
}
