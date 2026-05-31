'use client';
// app/components/ui/Sidebar.tsx
import { useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { PlusCircle, MessageSquare, LogOut, Zap, Trash2 } from 'lucide-react';
import { useConversations } from '../../hooks/useConversations';
import { useSupabase } from '../../hooks/useSupabase';

interface Props {
  onNewChat?: () => void;
}

export function Sidebar({ onNewChat }: Props) {
  const { conversations, loadConversations, deleteConversation } = useConversations();
  const { user, signOut } = useSupabase();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (user) loadConversations();
  }, [user, loadConversations]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    await deleteConversation(id);
    if (pathname === `/chat/${id}`) {
      router.push('/chat');
    }
  };

  return (
    <aside className="w-64 flex-shrink-0 bg-[#171717] border-r border-zinc-800 flex flex-col h-screen">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#10a37f] to-emerald-600 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="text-zinc-100 font-semibold text-lg tracking-tight">GptOmni</span>
        </div>
        <p className="text-xs text-zinc-500 mt-1 ml-9">Grounded · Verified · Cited</p>
      </div>

      {/* New Chat */}
      <div className="px-3 py-3">
        <Link
          href="/chat"
          onClick={onNewChat}
          className="flex items-center gap-2 w-full px-3 py-2 rounded-lg text-sm text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100 transition-colors group"
        >
          <PlusCircle className="w-4 h-4 text-zinc-500 group-hover:text-zinc-300" />
          New Chat
        </Link>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto px-3 py-1 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-xs text-zinc-600 text-center py-4">No conversations yet</p>
        )}
        {conversations.map(conv => {
          const isActive = pathname === `/chat/${conv.id}`;
          return (
            <div
              key={conv.id}
              className={`group flex items-center justify-between px-3 py-1.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-zinc-800 text-zinc-100'
                  : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
              }`}
            >
              <Link
                href={`/chat/${conv.id}`}
                className="flex items-center gap-2 truncate flex-1 min-w-0"
              >
                <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                <span className="truncate">{conv.title}</span>
              </Link>
              <button
                onClick={(e) => handleDelete(e, conv.id)}
                className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 transition-all ml-2 p-1 rounded hover:bg-zinc-700/50 flex-shrink-0"
                title="Delete chat"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>

      {/* User footer */}
      <div className="px-3 py-3 border-t border-zinc-800">
        {user && (
          <div className="flex items-center justify-between px-3 py-2">
            <div className="min-w-0">
              <p className="text-xs text-zinc-400 truncate">{user.email}</p>
            </div>
            <button
              onClick={() => signOut()}
              className="text-zinc-600 hover:text-zinc-300 transition-colors ml-2 flex-shrink-0"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
