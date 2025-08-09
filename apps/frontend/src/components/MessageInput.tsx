import React, { useState, useRef, useEffect } from 'react';
import { validateMessage } from '../utils/formatters';

interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  disabled = false,
  placeholder = "Ask me about patient data, predictions, or medical information...",
  className = '',
}) => {
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      const maxHeight = 120; // Max 5 lines approximately
      textarea.style.height = Math.min(scrollHeight, maxHeight) + 'px';
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [message]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage();
  };

  const sendMessage = () => {
    const validation = validateMessage(message);
    
    if (!validation.isValid) {
      setError(validation.error || 'Invalid message');
      return;
    }

    if (disabled) {
      setError('Cannot send message while processing');
      return;
    }

    const trimmedMessage = message.trim();
    setMessage('');
    setError(null);
    onSendMessage(trimmedMessage);

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      if (e.shiftKey) {
        // Allow new line with Shift+Enter
        return;
      } else {
        // Send message with Enter
        e.preventDefault();
        sendMessage();
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    if (error) {
      setError(null); // Clear error when user starts typing
    }
  };

  const isMessageValid = message.trim().length > 0;
  const charactersLeft = 4000 - message.length;
  const isNearLimit = charactersLeft < 100;

  return (
    <div className={`border-t bg-white ${className}`}>
      <form onSubmit={handleSubmit} className="p-4">
        <div className="flex flex-col space-y-2">
          {/* Error message */}
          {error && (
            <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-3 py-2">
              {error}
            </div>
          )}

          {/* Input area */}
          <div className="flex items-end space-x-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={message}
                onChange={handleChange}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                rows={1}
                className={`
                  w-full px-4 py-3 border border-gray-300 rounded-lg
                  focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                  resize-none overflow-hidden
                  placeholder-gray-500
                  ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}
                  ${error ? 'border-red-300 focus:ring-red-500' : ''}
                `}
                style={{ minHeight: '48px' }}
                aria-label="Type your message"
                aria-describedby={error ? 'message-error' : undefined}
              />
              
              {/* Character count */}
              {isNearLimit && (
                <div className={`absolute bottom-1 right-2 text-xs ${
                  charactersLeft < 0 ? 'text-red-500' : 'text-gray-500'
                }`}>
                  {charactersLeft}
                </div>
              )}
            </div>

            {/* Send button */}
            <button
              type="submit"
              disabled={disabled || !isMessageValid || charactersLeft < 0}
              className={`
                flex items-center justify-center w-12 h-12 rounded-lg
                transition-all duration-200
                ${disabled || !isMessageValid || charactersLeft < 0
                  ? 'bg-gray-200 cursor-not-allowed text-gray-400'
                  : 'bg-blue-500 hover:bg-blue-600 active:bg-blue-700 text-white hover:shadow-lg'
                }
              `}
              aria-label="Send message"
              title={disabled ? 'Processing...' : !isMessageValid ? 'Type a message' : 'Send message (Enter)'}
            >
              {disabled ? (
                <div className="animate-spin w-5 h-5 border-2 border-gray-400 border-t-transparent rounded-full" />
              ) : (
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              )}
            </button>
          </div>

          {/* Help text */}
          <div className="flex justify-between items-center text-xs text-gray-500">
            <span>Press Shift+Enter for new line, Enter to send</span>
            {!isNearLimit && (
              <span>{message.length}/4000</span>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};