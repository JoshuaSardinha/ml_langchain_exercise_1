import { useReducer, useCallback, useRef, useEffect, useMemo } from 'react';
import { 
  ChatState, 
  ChatAction, 
  ChatMessage, 
  MessageType,
  StreamProgressDto 
} from '../types/chat.types';
import { 
  generateSessionId, 
  createUserMessage, 
  createErrorMessage, 
  createSystemMessage 
} from '../utils/formatters';

// Initial state
const initialState: ChatState = {
  messages: [],
  isConnected: false,
  isLoading: false,
  isTyping: false,
  error: null,
  sessionId: generateSessionId(),
  currentProgress: undefined,
};

// Chat reducer
const chatReducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
        isLoading: false,
        isTyping: false,
        currentProgress: undefined,
      };

    case 'SET_CONNECTED':
      return {
        ...state,
        isConnected: action.payload,
        error: action.payload ? null : state.error,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
        error: action.payload ? null : state.error,
      };

    case 'SET_TYPING':
      return {
        ...state,
        isTyping: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
        isLoading: false,
        isTyping: false,
        currentProgress: undefined,
      };

    case 'SET_SESSION_ID':
      return {
        ...state,
        sessionId: action.payload,
      };

    case 'SET_PROGRESS':
      return {
        ...state,
        currentProgress: action.payload,
        isTyping: !!action.payload,
      };

    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: [],
        error: null,
        isLoading: false,
        isTyping: false,
        currentProgress: undefined,
      };

    case 'RESET_STATE':
      return {
        ...initialState,
        sessionId: generateSessionId(),
        isConnected: state.isConnected, // Keep connection status
      };

    default:
      return state;
  }
};

export interface UseChatStateReturn {
  state: ChatState;
  actions: {
    addMessage: (message: ChatMessage) => void;
    addUserMessage: (content: string) => ChatMessage;
    addSystemMessage: (content: string) => void;
    addErrorMessage: (content: string) => void;
    setConnected: (connected: boolean) => void;
    setLoading: (loading: boolean) => void;
    setTyping: (typing: boolean) => void;
    setError: (error: string | null) => void;
    setProgress: (progress: StreamProgressDto | undefined) => void;
    clearMessages: () => void;
    resetState: () => void;
    generateNewSession: () => void;
  };
}

export const useChatState = (): UseChatStateReturn => {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const sessionIdRef = useRef(state.sessionId);

  // Update ref when sessionId changes
  useEffect(() => {
    sessionIdRef.current = state.sessionId;
  }, [state.sessionId]);

  // Action creators
  const addMessage = useCallback((message: ChatMessage) => {
    dispatch({ type: 'ADD_MESSAGE', payload: message });
  }, []);

  const addUserMessage = useCallback((content: string): ChatMessage => {
    const userMessage = createUserMessage(content, sessionIdRef.current);
    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    return userMessage;
  }, []);

  const addSystemMessage = useCallback((content: string) => {
    const systemMessage = createSystemMessage(content, sessionIdRef.current);
    dispatch({ type: 'ADD_MESSAGE', payload: systemMessage });
  }, []);

  const addErrorMessage = useCallback((content: string) => {
    const errorMessage = createErrorMessage(content, sessionIdRef.current);
    dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
  }, []);

  const setConnected = useCallback((connected: boolean) => {
    dispatch({ type: 'SET_CONNECTED', payload: connected });
  }, []);

  const setLoading = useCallback((loading: boolean) => {
    dispatch({ type: 'SET_LOADING', payload: loading });
  }, []);

  const setTyping = useCallback((typing: boolean) => {
    dispatch({ type: 'SET_TYPING', payload: typing });
  }, []);

  const setError = useCallback((error: string | null) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  }, []);

  const setProgress = useCallback((progress: StreamProgressDto | undefined) => {
    dispatch({ type: 'SET_PROGRESS', payload: progress });
  }, []);

  const clearMessages = useCallback(() => {
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const resetState = useCallback(() => {
    dispatch({ type: 'RESET_STATE' });
  }, []);

  const generateNewSession = useCallback(() => {
    const newSessionId = generateSessionId();
    dispatch({ type: 'SET_SESSION_ID', payload: newSessionId });
    dispatch({ type: 'CLEAR_MESSAGES' });
  }, []);

  const actions = useMemo(
    () => ({
      addMessage,
      addUserMessage,
      addSystemMessage,
      addErrorMessage,
      setConnected,
      setLoading,
      setTyping,
      setError,
      setProgress,
      clearMessages,
      resetState,
      generateNewSession,
    }),
    [
      addMessage,
      addUserMessage,
      addSystemMessage,
      addErrorMessage,
      setConnected,
      setLoading,
      setTyping,
      setError,
      setProgress,
      clearMessages,
      resetState,
      generateNewSession,
    ]
  );

  return {
    state,
    actions,
  };
};