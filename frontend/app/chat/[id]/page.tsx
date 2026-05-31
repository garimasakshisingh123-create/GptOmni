'use client';
// app/chat/[id]/page.tsx
// Conversation page: loads messages, handles SSE pipeline stream

import { useEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { Square } from 'lucide-react';
import { Sidebar } from '../../components/ui/Sidebar';
import { ChatInput } from '../../components/chat/ChatInput';
import { AssistantMessage } from '../../components/chat/AssistantMessage';
import { TypingIndicator } from '../../components/chat/TypingIndicator';
import { usePipelineStream, PipelineStreamState } from '../../hooks/usePipelineStream';
import { useSupabase } from '../../hooks/useSupabase';
import { fetchMessages, sendChatMessage } from '../../lib/api';
import { Message } from '../../types/chat';

interface MessageWithPipeline extends Message {
  pipelineState?: PipelineStreamState;
}

export default function ConversationPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const conversationId = params.id as string;
  const { user } = useSupabase();

  const [messages, setMessages] = useState<MessageWithPipeline[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const pipeline = usePipelineStream();
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const queryProcessedRef = useRef(false);

  // Scroll to bottom
  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Reset query processed flag on conversation change
  useEffect(() => {
    queryProcessedRef.current = false;
  }, [conversationId]);

  // Load existing messages
  useEffect(() => {
    if (!conversationId) return;

    // Load from localStorage fallback first
    if (typeof window !== 'undefined') {
      const localMsgsStr = localStorage.getItem(`gptomni_messages_${conversationId}`);
      if (localMsgsStr) {
        try {
          const localMsgs = JSON.parse(localMsgsStr);
          setMessages(localMsgs);
        } catch (e) {
          console.error('Error loading local messages:', e);
        }
      }
    }

    fetchMessages(conversationId)
      .then(data => {
        const apiMsgs = data.messages || [];
        if (apiMsgs.length > 0) {
          setMessages(apiMsgs);
          if (typeof window !== 'undefined') {
            localStorage.setItem(`gptomni_messages_${conversationId}`, JSON.stringify(apiMsgs));
          }
        }
      })
      .catch(err => {
        console.error('Failed to load messages from API:', err);
      });
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, pipeline.streamingAnswer]);

  const handleAbort = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  const handleSend = async (text: string) => {
    if (!user || isLoading) return;

    // Add user message immediately
    const userMsg: MessageWithPipeline = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId,
      user_id: user.id,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    
    setMessages(prev => {
      const updated = [...prev, userMsg];
      if (typeof window !== 'undefined') {
        localStorage.setItem(`gptomni_messages_${conversationId}`, JSON.stringify(updated));
      }
      return updated;
    });

    setIsLoading(true);
    pipeline.reset();

    // Create a temporary assistant message slot for streaming
    const tempAssistantId = `streaming-${Date.now()}`;

    // Set up abort controller
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const response = await sendChatMessage(text, conversationId, abortController.signal);

      // Consume the SSE stream
      await pipeline.consumeStream(response);

      // Add the completed assistant message
      const assistantMsg: MessageWithPipeline = {
        id: tempAssistantId,
        conversation_id: conversationId,
        user_id: user.id,
        role: 'assistant',
        content: pipeline.streamingAnswer,
        created_at: new Date().toISOString(),
        pipelineState: { ...pipeline },
      };
      
      setMessages(prev => {
        const updated = [...prev, assistantMsg];
        if (typeof window !== 'undefined') {
          localStorage.setItem(`gptomni_messages_${conversationId}`, JSON.stringify(updated));
        }
        return updated;
      });

    } catch (e: unknown) {
      if (abortController.signal.aborted) {
        // Interrupted by stop generating
        const partialAnswer = pipeline.streamingAnswer || "Generation stopped.";
        const assistantMsg: MessageWithPipeline = {
          id: tempAssistantId,
          conversation_id: conversationId,
          user_id: user.id,
          role: 'assistant',
          content: partialAnswer,
          created_at: new Date().toISOString(),
          pipelineState: { ...pipeline, isComplete: false },
        };
        
        setMessages(prev => {
          const updated = [...prev, assistantMsg];
          if (typeof window !== 'undefined') {
            localStorage.setItem(`gptomni_messages_${conversationId}`, JSON.stringify(updated));
          }
          return updated;
        });
      } else {
        const errMsg: MessageWithPipeline = {
          id: `err-${Date.now()}`,
          conversation_id: conversationId,
          user_id: user.id,
          role: 'assistant',
          content: `**Error:** ${e instanceof Error ? e.message : 'Something went wrong. Please try again.'}`,
          created_at: new Date().toISOString(),
        };
        setMessages(prev => {
          const updated = [...prev, errMsg];
          if (typeof window !== 'undefined') {
            localStorage.setItem(`gptomni_messages_${conversationId}`, JSON.stringify(updated));
          }
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  // Handle ?q= query param (redirect from new chat page)
  useEffect(() => {
    const q = searchParams.get('q');
    if (q && !queryProcessedRef.current) {
      queryProcessedRef.current = true;
      handleSend(q);

      // Clean up the URL query param so a page refresh doesn't trigger it again
      if (typeof window !== 'undefined') {
        const newUrl = window.location.pathname;
        window.history.replaceState({}, '', newUrl);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, conversationId]);

  return (
    <div className="flex h-screen bg-[#212121]">
      <Sidebar />

      <main className="flex-1 flex flex-col min-w-0 bg-[#212121]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="py-4">
            {messages.length === 0 && !isLoading && (
              <div className="text-center py-16 text-zinc-600">
                <p className="text-sm">Start a conversation...</p>
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id}>
                {msg.role === 'user' ? (
                  /* User message — right-aligned bubble */
                  <div className="py-3 px-4 max-w-3xl mx-auto">
                    <div className="flex justify-end">
                      <div className="max-w-[75%] bg-[#2f2f2f] border border-zinc-700 rounded-2xl rounded-tr-sm px-4 py-3">
                        <p className="text-sm text-zinc-100 leading-relaxed whitespace-pre-wrap">
                          {msg.content}
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Assistant message — full width with IE panel */
                  <AssistantMessage
                    content={msg.content}
                    stages={msg.pipelineState?.stages}
                    sources={msg.pipelineState?.sources}
                    claims={msg.pipelineState?.claims}
                    verificationResults={msg.pipelineState?.verificationResults}
                    provenance={msg.pipelineState?.provenance}
                    isComplete={msg.pipelineState?.isComplete ?? true}
                    currentStageNumber={msg.pipelineState?.currentStageNumber ?? 0}
                    runId={msg.pipelineState?.runId}
                    showIE={!!msg.pipelineState}
                  />
                )}
              </div>
            ))}

            {/* Streaming state */}
            {isLoading && (
              <>
                {pipeline.currentStageNumber === 0 ? (
                  <TypingIndicator />
                ) : (
                  <AssistantMessage
                    content={pipeline.streamingAnswer || (pipeline.currentStageNumber >= 6 ? '✍️ Generating grounded response...' : '')}
                    stages={pipeline.stages}
                    sources={pipeline.sources}
                    claims={pipeline.claims}
                    verificationResults={pipeline.verificationResults}
                    provenance={pipeline.provenance}
                    isComplete={false}
                    currentStageNumber={pipeline.currentStageNumber}
                    runId={pipeline.runId}
                    showIE={true}
                  />
                )}
              </>
            )}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Stop Generating Button */}
        {isLoading && (
          <div className="flex justify-center mb-2 animate-in fade-in duration-200">
            <button
              onClick={handleAbort}
              className="flex items-center gap-2 px-4 py-2 bg-[#2f2f2f] hover:bg-zinc-800 text-zinc-200 border border-zinc-700 rounded-lg text-xs font-semibold shadow-lg transition-all active:scale-95"
            >
              <Square className="w-3 h-3 fill-red-500 text-red-500" />
              Stop Generating
            </button>
          </div>
        )}

        {/* Input */}
        <ChatInput onSend={handleSend} disabled={isLoading} />
      </main>
    </div>
  );
}
