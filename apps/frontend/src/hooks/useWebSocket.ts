import { useState, useEffect, useRef, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { 
  ChatMessageRequest, 
  ChatMessageResponse, 
  ConnectionStatus, 
  StreamProgressDto 
} from '../types/chat.types';

interface UseWebSocketOptions {
  url?: string;
  autoConnect?: boolean;
  reconnectionAttempts?: number;
  reconnectionDelay?: number;
}

interface UseWebSocketReturn {
  socket: Socket | null;
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  error: string | null;
  sendMessage: (message: ChatMessageRequest) => Promise<void>;
  connect: () => void;
  disconnect: () => void;
  onMessage: (callback: (response: ChatMessageResponse) => void) => void;
  onProgress: (callback: (progress: StreamProgressDto) => void) => void;
  onError: (callback: (error: string) => void) => void;
  removeAllListeners: () => void;
}

export const useWebSocket = (options: UseWebSocketOptions = {}): UseWebSocketReturn => {
  const {
    url = 'http://localhost:3000/chat',
    autoConnect = true,
    reconnectionAttempts = 3,
    reconnectionDelay = 1000
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(ConnectionStatus.DISCONNECTED);
  const [error, setError] = useState<string | null>(null);
  
  const socketRef = useRef<Socket | null>(null);
  const messageCallbackRef = useRef<((response: ChatMessageResponse) => void) | null>(null);
  const progressCallbackRef = useRef<((progress: StreamProgressDto) => void) | null>(null);
  const errorCallbackRef = useRef<((error: string) => void) | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const attemptReconnect = useCallback(() => {
    if (reconnectCountRef.current >= reconnectionAttempts) {
      setConnectionStatus(ConnectionStatus.ERROR);
      setError(`Failed to reconnect after ${reconnectionAttempts} attempts. Please check your connection and try again.`);
      return;
    }

    reconnectCountRef.current += 1;
    setConnectionStatus(ConnectionStatus.RECONNECTING);
    setError(null);

    // Exponential backoff: 1s, 2s, 4s, etc.
    const backoffDelay = reconnectionDelay * Math.pow(2, reconnectCountRef.current - 1);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (socketRef.current) {
        console.log(`Attempting reconnection ${reconnectCountRef.current}/${reconnectionAttempts}`);
        socketRef.current.connect();
      }
    }, backoffDelay);
  }, [reconnectionAttempts, reconnectionDelay]);

  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    setConnectionStatus(ConnectionStatus.CONNECTING);
    setError(null);

    // Create new socket connection
    socketRef.current = io(url, {
      transports: ['websocket', 'polling'],
      upgrade: true,
      timeout: 20000,
      forceNew: true,
      reconnection: false, // We handle reconnection manually
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('Socket connected:', socket.id);
      setIsConnected(true);
      setConnectionStatus(ConnectionStatus.CONNECTED);
      setError(null);
      reconnectCountRef.current = 0;
      clearReconnectTimeout();
    });

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setIsConnected(false);
      setConnectionStatus(ConnectionStatus.DISCONNECTED);
      
      // Attempt reconnection for certain disconnect reasons
      if (reason === 'io server disconnect' || reason === 'io client disconnect') {
        // Manual disconnect, don't reconnect
        return;
      }
      
      // Automatic reconnection for other reasons
      attemptReconnect();
    });

    socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      setIsConnected(false);
      
      // Provide more descriptive error messages
      let errorMessage = 'Connection failed';
      if (error.message?.includes('ECONNREFUSED')) {
        errorMessage = 'Unable to connect to server. Please check if the server is running.';
      } else if (error.message?.includes('timeout')) {
        errorMessage = 'Connection timeout. Please check your network connection.';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      attemptReconnect();
    });

    // Chat event handlers
    socket.on('response', (response: ChatMessageResponse) => {
      if (messageCallbackRef.current) {
        messageCallbackRef.current(response);
      }
    });

    socket.on('progress', (progress: StreamProgressDto) => {
      if (progressCallbackRef.current) {
        progressCallbackRef.current(progress);
      }
    });

    socket.on('error', (error: { message: string }) => {
      const errorMessage = error?.message || 'An error occurred';
      setError(errorMessage);
      if (errorCallbackRef.current) {
        errorCallbackRef.current(errorMessage);
      }
    });

    socket.on('exception', (error: any) => {
      const errorMessage = error?.message || error || 'An exception occurred';
      setError(errorMessage);
      if (errorCallbackRef.current) {
        errorCallbackRef.current(errorMessage);
      }
    });

  }, [url, attemptReconnect, clearReconnectTimeout]);

  const disconnect = useCallback(() => {
    clearReconnectTimeout();
    reconnectCountRef.current = 0;
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    
    setIsConnected(false);
    setConnectionStatus(ConnectionStatus.DISCONNECTED);
    setError(null);
  }, [clearReconnectTimeout]);

  const sendMessage = useCallback(async (message: ChatMessageRequest): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (!socketRef.current?.connected) {
        reject(new Error('Socket not connected'));
        return;
      }

      // Send message with acknowledgment
      socketRef.current.emit('message', message, (response: { success: boolean; error?: string }) => {
        if (response.success) {
          resolve();
        } else {
          reject(new Error(response.error || 'Failed to send message'));
        }
      });
    });
  }, []);

  const onMessage = useCallback((callback: (response: ChatMessageResponse) => void) => {
    messageCallbackRef.current = callback;
  }, []);

  const onProgress = useCallback((callback: (progress: StreamProgressDto) => void) => {
    progressCallbackRef.current = callback;
  }, []);

  const onError = useCallback((callback: (error: string) => void) => {
    errorCallbackRef.current = callback;
  }, []);

  const removeAllListeners = useCallback(() => {
    messageCallbackRef.current = null;
    progressCallbackRef.current = null;
    errorCallbackRef.current = null;
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      clearReconnectTimeout();
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [autoConnect, connect, clearReconnectTimeout]);

  // Handle page visibility changes to reconnect when page becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !socketRef.current?.connected) {
        connect();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [connect]);

  return {
    socket: socketRef.current,
    isConnected,
    connectionStatus,
    error,
    sendMessage,
    connect,
    disconnect,
    onMessage,
    onProgress,
    onError,
    removeAllListeners,
  };
};