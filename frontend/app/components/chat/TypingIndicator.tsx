'use client';
// app/components/chat/TypingIndicator.tsx
export function TypingIndicator() {
  return (
    <div className="flex items-center gap-3 py-4 px-4 max-w-3xl mx-auto">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#10a37f] to-emerald-600 flex items-center justify-center flex-shrink-0">
        <span className="text-white text-xs font-bold">G</span>
      </div>
      <div className="flex items-center gap-1 bg-zinc-800/50 rounded-xl px-4 py-3">
        <div className="flex gap-1.5 items-center">
          <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 rounded-full bg-zinc-500 animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-xs text-zinc-500 ml-2">GptOmni is thinking...</span>
      </div>
    </div>
  );
}
