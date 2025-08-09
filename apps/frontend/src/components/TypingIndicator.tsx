import React from 'react';
import { StreamProgressDto } from '../types/chat.types';

interface TypingIndicatorProps {
  isVisible: boolean;
  progress?: StreamProgressDto;
  className?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  isVisible,
  progress,
  className = '',
}) => {
  if (!isVisible) {
    return null;
  }

  const getProgressColor = (stage: string) => {
    switch (stage) {
      case 'analyzing':
        return 'bg-blue-500';
      case 'processing':
        return 'bg-yellow-500';
      case 'complete':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStageIcon = (stage: string) => {
    switch (stage) {
      case 'analyzing':
        return '🔍';
      case 'processing':
        return '⚙️';
      case 'complete':
        return '✅';
      default:
        return '💭';
    }
  };

  return (
    <div className={`flex items-start space-x-2 mb-4 ${className}`}>
      {/* AI Avatar */}
      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm">
        🤖
      </div>

      {/* Typing bubble */}
      <div className="bg-white border border-gray-200 rounded-lg rounded-bl-none shadow-sm px-4 py-3 max-w-sm">
        {progress ? (
          <div className="space-y-2">
            {/* Progress message with icon */}
            <div className="flex items-center space-x-2">
              <span className="text-sm">{getStageIcon(progress.stage)}</span>
              <span className="text-sm text-gray-700">{progress.message}</span>
            </div>

            {/* Progress bar */}
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div 
                className={`h-1.5 rounded-full transition-all duration-300 ${getProgressColor(progress.stage)}`}
                style={{ width: `${progress.progress}%` }}
              />
            </div>

            {/* Progress percentage */}
            <div className="text-xs text-gray-500 text-right">
              {progress.progress}%
            </div>
          </div>
        ) : (
          <div className="flex items-center space-x-1">
            {/* Simple typing animation */}
            <span className="text-sm text-gray-600">Thinking</span>
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};