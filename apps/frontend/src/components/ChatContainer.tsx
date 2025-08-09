import React, { useEffect, useCallback } from 'react';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { useWebSocket } from '../hooks/useWebSocket';
import { useChatState } from '../hooks/useChatState';
import { 
  ChatMessage, 
  MessageType, 
  ConnectionStatus,
  ChatMessageResponse 
} from '../types/chat.types';
import { generateMessageId, parseErrorMessage } from '../utils/formatters';

interface ChatContainerProps {
  className?: string;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  className = '',
}) => {
  const { state, actions } = useChatState();
  const {
    isConnected,
    connectionStatus,
    error: wsError,
    sendMessage,
    onMessage,
    onProgress,
    onError,
    connect,
  } = useWebSocket();

  // Update connection status
  useEffect(() => {
    actions.setConnected(isConnected);
  }, [isConnected, actions]);

  // Handle WebSocket errors
  useEffect(() => {
    if (wsError) {
      actions.setError(wsError);
    }
  }, [wsError, actions]);

  // Set up WebSocket event listeners
  useEffect(() => {
    // Handle incoming messages
    onMessage((response: ChatMessageResponse) => {
      const assistantMessage: ChatMessage = {
        id: generateMessageId(),
        content: response.message,
        type: response.type || MessageType.ASSISTANT,
        timestamp: new Date(response.timestamp),
        sessionId: response.sessionId,
        citations: response.citations,
        chartData: response.chartData,
        metadata: response.metadata,
      };

      actions.addMessage(assistantMessage);
      actions.setLoading(false);
      actions.setTyping(false);
    });

    // Handle progress updates
    onProgress((progress) => {
      actions.setProgress(progress);
    });

    // Handle errors
    onError((error) => {
      actions.addErrorMessage(parseErrorMessage(error));
      actions.setLoading(false);
      actions.setError(error);
    });

    return () => {
      // Cleanup event listeners when component unmounts
    };
  }, [onMessage, onProgress, onError, actions]);

  // Handle sending messages
  const handleSendMessage = useCallback(async (messageContent: string) => {
    if (!isConnected) {
      actions.addErrorMessage('Not connected to server. Please check your connection.');
      return;
    }

    // Add user message to chat
    const userMessage = actions.addUserMessage(messageContent);
    actions.setLoading(true);
    actions.setError(null);

    try {
      // Send message via WebSocket
      await sendMessage({
        message: messageContent,
        sessionId: state.sessionId,
        context: {
          timestamp: new Date().toISOString(),
          messageId: userMessage.id,
        },
      });
    } catch (error) {
      const errorMessage = parseErrorMessage(error);
      actions.addErrorMessage(`Failed to send message: ${errorMessage}`);
      actions.setLoading(false);
      actions.setError(errorMessage);
    }
  }, [isConnected, sendMessage, state.sessionId, actions]);

  // Handle connection retry
  const handleRetryConnection = useCallback(() => {
    actions.setError(null);
    connect();
  }, [connect, actions]);

  // Handle clearing chat
  const handleClearChat = useCallback(() => {
    actions.generateNewSession();
    actions.addSystemMessage('New conversation started');
  }, [actions]);

  // Connection status indicator
  const getConnectionStatusIndicator = () => {
    switch (connectionStatus) {
      case ConnectionStatus.CONNECTING:
        return (
          <div className="flex items-center space-x-2 text-yellow-600">
            <div className="animate-spin w-4 h-4 border-2 border-yellow-600 border-t-transparent rounded-full" />
            <span className="text-sm">Connecting...</span>
          </div>
        );
      case ConnectionStatus.RECONNECTING:
        return (
          <div className="flex items-center space-x-2 text-yellow-600">
            <div className="animate-spin w-4 h-4 border-2 border-yellow-600 border-t-transparent rounded-full" />
            <span className="text-sm">Reconnecting...</span>
          </div>
        );
      case ConnectionStatus.DISCONNECTED:
      case ConnectionStatus.ERROR:
        return (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-red-600">
              <div className="w-4 h-4 bg-red-600 rounded-full" />
              <span className="text-sm">Disconnected</span>
            </div>
            <button
              onClick={handleRetryConnection}
              className="text-sm text-blue-600 hover:text-blue-800 underline"
            >
              Retry
            </button>
          </div>
        );
      case ConnectionStatus.CONNECTED:
      default:
        return (
          <div className="flex items-center space-x-2 text-green-600">
            <div className="w-4 h-4 bg-green-600 rounded-full" />
            <span className="text-sm">Connected</span>
          </div>
        );
    }
  };

  return (
    <div className={`flex flex-col h-full bg-gray-50 ${className}`}>
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between max-w-4xl mx-auto">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Data Doctor</h1>
            <p className="text-sm text-gray-600">Your AI Health Assistant</p>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Connection status */}
            <div className="hidden sm:block">
              {getConnectionStatusIndicator()}
            </div>
            
            {/* Clear chat button */}
            <button
              onClick={handleClearChat}
              className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              title="Start new conversation"
            >
              Clear Chat
            </button>
          </div>
        </div>
      </header>

      {/* Mobile connection status */}
      <div className="sm:hidden bg-white border-b border-gray-200 px-4 py-2">
        {getConnectionStatusIndicator()}
      </div>

      {/* Error banner */}
      {state.error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-red-600">⚠️</span>
                <span className="text-red-800 text-sm">{state.error}</span>
              </div>
              <button
                onClick={() => actions.setError(null)}
                className="text-red-600 hover:text-red-800"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main chat area */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full overflow-hidden">
        {/* Messages */}
        <MessageList
          messages={state.messages}
          isTyping={state.isTyping}
          currentProgress={state.currentProgress}
          className="flex-1"
        />

        {/* Input */}
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={!isConnected || state.isLoading}
          placeholder={
            !isConnected 
              ? "Connecting to server..." 
              : state.isLoading 
                ? "Processing your message..."
                : "Ask me about patient data, predictions, or medical information..."
          }
        />
      </div>
    </div>
  );
};