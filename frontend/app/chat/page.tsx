'use client';
// app/chat/page.tsx
// New chat page — shows welcome screen and allows initiating a conversation

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Zap } from 'lucide-react';
import { useSupabase } from '../hooks/useSupabase';
import { useConversations } from '../hooks/useConversations';
import { Sidebar } from '../components/ui/Sidebar';
import { ChatInput } from '../components/chat/ChatInput';

export default function ChatPage() {
  const { user, loading } = useSupabase();
  const { createConversation } = useConversations();
  const router = useRouter();

  const handleSend = async (text: string) => {
    if (!user) return;
    try {
      const convId = await createConversation(text.slice(0, 60));
      if (convId) {
        router.push(`/chat/${convId}?q=${encodeURIComponent(text)}`);
      }
    } catch (e) {
      console.error('Error starting conversation:', e);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#212121]">
        <div className="w-8 h-8 rounded-full border-2 border-[#10a37f] border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#212121]">
      <Sidebar />
      <main className="flex-1 flex flex-col">
        {/* Welcome area */}
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-[#10a37f] to-emerald-600 mb-4 shadow-lg shadow-emerald-900/30">
              <Zap className="w-7 h-7 text-white" />
            </div>
            <h1 className="text-3xl font-bold text-zinc-100">GptOmni</h1>
            <p className="text-zinc-400 mt-2 max-w-md">
              Every answer is grounded in real-time retrieved evidence,
              verified claim by claim, with full source provenance.
            </p>
          </div>

          {/* Example queries */}
          <div className="grid grid-cols-2 gap-2 mb-8 max-w-2xl w-full">
            {[
              'What is the current Fed interest rate?',
              'Is Ozempic FDA approved for weight loss?',
              'Latest breakthroughs in quantum computing',
              'What causes inflation?',
            ].map(q => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                className="text-left px-4 py-3 rounded-xl bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-600 text-sm text-zinc-300 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        <ChatInput onSend={handleSend} />
      </main>
    </div>
  );
}
