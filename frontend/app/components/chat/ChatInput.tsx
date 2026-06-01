'use client';
// app/components/chat/ChatInput.tsx
import { useState, useRef, KeyboardEvent, useEffect } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isSubmittingRef = useRef(false);

  // Reset our submission guard once the disabled prop goes back to false
  useEffect(() => {
    if (!disabled) {
      isSubmittingRef.current = false;
    }
  }, [disabled]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled || isSubmittingRef.current) return;
    
    isSubmittingRef.current = true;
    onSend(trimmed);
    setValue('');
    // Reset height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const lineHeight = 24;
    const maxLines = 6;
    el.style.height = Math.min(el.scrollHeight, lineHeight * maxLines) + 'px';
  };

  return (
    <div className="border-t border-zinc-800 bg-[#212121] px-4 py-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-3 bg-[#2f2f2f] border border-zinc-700 rounded-xl px-4 py-3 focus-within:border-zinc-500 transition-colors">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={e => setValue(e.target.value)}
            onInput={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={disabled ? 'Waiting for response...' : 'Message GptOmni...'}
            rows={1}
            className="flex-1 bg-transparent text-zinc-100 placeholder-zinc-500 resize-none outline-none text-sm leading-6 min-h-[24px] max-h-36"
          />
          <button
            onClick={handleSend}
            disabled={disabled || !value.trim()}
            className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
              disabled || !value.trim()
                ? 'bg-zinc-700 text-zinc-500 cursor-not-allowed'
                : 'bg-[#10a37f] text-white hover:bg-emerald-600 active:scale-95'
            }`}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-zinc-600 text-center mt-2">
          GptOmni verifies every claim. Answers may take 15-30s.
        </p>
      </div>
    </div>
  );
}
