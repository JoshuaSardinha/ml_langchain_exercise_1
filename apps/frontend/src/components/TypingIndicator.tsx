import React, { useEffect, useState } from 'react';
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
  const [showIndicator, setShowIndicator] = useState(false);

  // Add a small delay before showing the indicator to prevent flashing
  useEffect(() => {
    if (isVisible) {
      const timer = setTimeout(() => {
        setShowIndicator(true);
      }, 300); // 300ms delay
      
      return () => clearTimeout(timer);
    } else {
      setShowIndicator(false);
    }
  }, [isVisible]);

  if (!showIndicator) {
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

  const getStageDescription = (stage: string) => {
    switch (stage) {
      case 'analyzing':
        return 'Analyzing your request';
      case 'processing':
        return 'Processing data';
      case 'complete':
        return 'Finalizing response';
      default:
        return 'Thinking';
    }
  };

  return (
    <div 
      className={`flex items-start space-x-2 mb-4 animate-fadeIn ${className}`}
      role="status"
      aria-live="polite"
      aria-label={progress ? `AI is ${getStageDescription(progress.stage).toLowerCase()}, ${progress.progress}% complete` : "AI is thinking"}
    >
      {/* AI Avatar with subtle pulse animation */}
      <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-sm animate-pulse">
        🤖
      </div>

      {/* Typing bubble with enhanced styling */}
      <div className="bg-white border border-gray-200 rounded-lg rounded-bl-none shadow-sm px-4 py-3 max-w-sm animate-slideInFromLeft">
        {progress ? (
          <div className="space-y-2" aria-describedby="progress-description">
            {/* Progress message with icon */}
            <div className="flex items-center space-x-2">
              <span className="text-sm animate-pulse" aria-hidden="true">
                {getStageIcon(progress.stage)}
              </span>
              <span className="text-sm text-gray-700 font-medium">
                {progress.message || getStageDescription(progress.stage)}
              </span>
            </div>

            {/* Enhanced progress bar */}
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div 
                className={`h-2 rounded-full transition-all duration-500 ease-out ${getProgressColor(progress.stage)} relative`}
                style={{ width: `${Math.max(5, progress.progress)}%` }}
              >
                {/* Animated shimmer effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white via-transparent opacity-30 animate-shimmer" />
              </div>
            </div>

            {/* Progress percentage with better formatting */}
            <div className="flex justify-between items-center">
              <span className="text-xs text-gray-500">
                {getStageDescription(progress.stage)}
              </span>
              <span className="text-xs text-gray-600 font-medium">
                {progress.progress}%
              </span>
            </div>
          </div>
        ) : (
          <div className="flex items-center space-x-2">
            {/* Enhanced thinking animation */}
            <div className="flex items-center space-x-1">
              <span className="text-sm text-gray-600 font-medium">AI is thinking</span>
              <div className="flex space-x-1 ml-2">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};