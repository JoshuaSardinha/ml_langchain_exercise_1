import { ChatMessage, MessageType } from '../types/chat.types';

/**
 * Format timestamp for display in chat messages
 */
export const formatTimestamp = (timestamp: Date): string => {
  const now = new Date();
  const messageDate = new Date(timestamp);
  const diffInSeconds = Math.floor((now.getTime() - messageDate.getTime()) / 1000);
  
  if (diffInSeconds < 60) {
    return 'Just now';
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes}m ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours}h ago`;
  } else {
    return messageDate.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
};

/**
 * Generate a unique message ID
 */
export const generateMessageId = (): string => {
  return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
};

/**
 * Generate a unique session ID
 */
export const generateSessionId = (): string => {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
};

/**
 * Get CSS classes for message bubble based on type
 */
export const getMessageBubbleClasses = (type: MessageType): string => {
  const baseClasses = 'max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow-sm';
  
  switch (type) {
    case MessageType.USER:
      return `${baseClasses} bg-blue-500 text-white ml-auto rounded-br-none`;
    case MessageType.ASSISTANT:
      return `${baseClasses} bg-white text-gray-900 border border-gray-200 mr-auto rounded-bl-none`;
    case MessageType.SYSTEM:
      return `${baseClasses} bg-gray-100 text-gray-700 mx-auto text-center text-sm`;
    case MessageType.ERROR:
      return `${baseClasses} bg-red-100 text-red-800 border border-red-200 mx-auto`;
    default:
      return baseClasses;
  }
};

/**
 * Get icon for message type
 */
export const getMessageTypeIcon = (type: MessageType): string => {
  switch (type) {
    case MessageType.USER:
      return '👤';
    case MessageType.ASSISTANT:
      return '🤖';
    case MessageType.SYSTEM:
      return 'ℹ️';
    case MessageType.ERROR:
      return '⚠️';
    default:
      return '';
  }
};

/**
 * Truncate text to a maximum length
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength - 3) + '...';
};

/**
 * Parse error message from server response
 */
export const parseErrorMessage = (error: any): string => {
  if (typeof error === 'string') return error;
  if (error?.message) return error.message;
  if (error?.response?.data?.message) return error.response.data.message;
  return 'An unexpected error occurred';
};

/**
 * Create a user message object
 */
export const createUserMessage = (content: string, sessionId: string): ChatMessage => {
  return {
    id: generateMessageId(),
    content,
    type: MessageType.USER,
    timestamp: new Date(),
    sessionId,
  };
};

/**
 * Create a system message object
 */
export const createSystemMessage = (content: string, sessionId: string): ChatMessage => {
  return {
    id: generateMessageId(),
    content,
    type: MessageType.SYSTEM,
    timestamp: new Date(),
    sessionId,
  };
};

/**
 * Create an error message object
 */
export const createErrorMessage = (content: string, sessionId: string): ChatMessage => {
  return {
    id: generateMessageId(),
    content,
    type: MessageType.ERROR,
    timestamp: new Date(),
    sessionId,
  };
};

/**
 * Validate message content
 */
export const validateMessage = (message: string): { isValid: boolean; error?: string } => {
  if (!message || typeof message !== 'string') {
    return { isValid: false, error: 'Message cannot be empty' };
  }
  
  const trimmed = message.trim();
  if (trimmed.length === 0) {
    return { isValid: false, error: 'Message cannot be empty' };
  }
  
  if (trimmed.length > 4000) {
    return { isValid: false, error: 'Message is too long (max 4000 characters)' };
  }
  
  return { isValid: true };
};