import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage, MessageType } from '../types/chat.types';
import { formatTimestamp, getMessageBubbleClasses, getMessageTypeIcon } from '../utils/formatters';
import { ChartRenderer } from './ChartRenderer';
import { CitationCard } from './CitationCard';

interface MessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isUser }) => {
  const { content, type, timestamp, citations, chartData, metadata } = message;
  const bubbleClasses = getMessageBubbleClasses(type);
  const typeIcon = getMessageTypeIcon(type);

  const renderContent = () => {
    // For user messages, render plain text
    if (type === MessageType.USER) {
      return <div className="whitespace-pre-wrap">{content}</div>;
    }

    // For system/error messages, render plain text
    if (type === MessageType.SYSTEM || type === MessageType.ERROR) {
      return <div className="whitespace-pre-wrap">{content}</div>;
    }

    // For assistant messages, render markdown
    return (
      <div className="prose prose-sm max-w-none">
        <ReactMarkdown
          components={{
            // Customize markdown rendering
            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
            ul: ({ children }) => <ul className="list-disc list-inside mb-2">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal list-inside mb-2">{children}</ol>,
            li: ({ children }) => <li className="mb-1">{children}</li>,
            code: ({ children }) => (
              <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono">
                {children}
              </code>
            ),
            pre: ({ children }) => (
              <pre className="bg-gray-100 text-gray-800 p-2 rounded overflow-x-auto text-sm font-mono">
                {children}
              </pre>
            ),
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} mb-4`}>
      {/* Message bubble */}
      <div className="flex items-start space-x-2 max-w-full">
        {/* Avatar/Icon for non-user messages */}
        {!isUser && type !== MessageType.SYSTEM && (
          <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm">
            {typeIcon}
          </div>
        )}
        
        <div className={`${bubbleClasses} ${isUser ? '' : 'max-w-3xl'}`}>
          {/* Error indicator */}
          {type === MessageType.ERROR && (
            <div className="flex items-center space-x-2 mb-2">
              <span className="text-red-600">{typeIcon}</span>
              <span className="text-red-800 font-medium text-sm">Error</span>
            </div>
          )}

          {/* Message content */}
          {renderContent()}

          {/* Chart visualization */}
          {chartData && (
            <div className="mt-3">
              <ChartRenderer chartData={chartData} />
            </div>
          )}

          {/* Citations */}
          {citations && citations.length > 0 && (
            <div className="mt-3">
              <CitationCard citations={citations} />
            </div>
          )}

          {/* Processing info */}
          {metadata?.processingTime && type === MessageType.ASSISTANT && (
            <div className="text-xs text-gray-500 mt-2">
              Processed in {metadata.processingTime}ms
            </div>
          )}
        </div>

        {/* Avatar/Icon for user messages */}
        {isUser && (
          <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-sm text-white">
            {typeIcon}
          </div>
        )}
      </div>

      {/* Timestamp */}
      <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'mr-10' : 'ml-10'}`}>
        {formatTimestamp(timestamp)}
      </div>
    </div>
  );
};