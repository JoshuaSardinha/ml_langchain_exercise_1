import React, { useEffect, useRef } from 'react';
import { ChatMessage, MessageType } from '../types/chat.types';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

interface MessageListProps {
  messages: ChatMessage[];
  isTyping: boolean;
  currentProgress?: any;
  className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isTyping,
  currentProgress,
  className = '',
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!containerRef.current) return;

      switch (event.key) {
        case 'Home':
          if (event.ctrlKey) {
            containerRef.current.scrollTo({ top: 0, behavior: 'smooth' });
            event.preventDefault();
          }
          break;
        case 'End':
          if (event.ctrlKey) {
            scrollToBottom();
            event.preventDefault();
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (messages.length === 0 && !isTyping) {
    return (
      <div className={`flex-1 flex items-center justify-center ${className}`}>
        <div className="text-center max-w-md mx-auto px-4">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">🤖</span>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Welcome to Data Doctor
          </h3>
          <p className="text-gray-600 mb-4">
            I'm your AI health assistant. Ask me questions about patient data, 
            request predictions, or search through medical documents.
          </p>
          <div className="text-left text-sm text-gray-500 space-y-1">
            <p><strong>Try asking:</strong></p>
            <p>• "How many smokers are in the dataset?"</p>
            <p>• "Predict COPD for a 55-year-old male with BMI 27.5"</p>
            <p>• "What are the symptoms of seasonal allergies?"</p>
            <p>• "Compare readmitted vs non-readmitted patients"</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4 ${className}`}
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {/* Welcome message for first conversation */}
      {messages.length === 0 && (
        <div className="text-center py-8">
          <div className="bg-blue-50 rounded-lg p-6 max-w-md mx-auto">
            <h3 className="text-blue-800 font-medium mb-2">Welcome to Data Doctor!</h3>
            <p className="text-blue-700 text-sm">
              Start by asking a question about patient data or medical information.
            </p>
          </div>
        </div>
      )}

      {/* Message list */}
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          isUser={message.type === MessageType.USER}
        />
      ))}

      {/* Typing indicator */}
      {isTyping && (
        <TypingIndicator 
          isVisible={isTyping} 
          progress={currentProgress}
        />
      )}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  );
};