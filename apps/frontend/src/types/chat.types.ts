// Message Types
export enum MessageType {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  ERROR = 'error',
}

export interface Citation {
  documentId: string;
  title: string;
  excerpt: string;
  page?: number;
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  data: any;
  options?: any;
}

export interface ChatMessage {
  id: string;
  content: string;
  type: MessageType;
  timestamp: Date;
  sessionId: string;
  citations?: Citation[];
  chartData?: ChartData;
  metadata?: Record<string, any>;
}

// WebSocket Events
export interface ChatMessageRequest {
  message: string;
  sessionId?: string;
  context?: Record<string, any>;
}

export interface ChatMessageResponse {
  message: string;
  type: MessageType;
  sessionId: string;
  timestamp: Date;
  citations?: Citation[];
  chartData?: ChartData;
  metadata?: Record<string, any>;
}

export interface StreamProgressDto {
  stage: 'analyzing' | 'processing' | 'complete';
  progress: number;
  message: string;
}

// Chat State Types
export interface ChatState {
  messages: ChatMessage[];
  isConnected: boolean;
  isLoading: boolean;
  isTyping: boolean;
  error: string | null;
  sessionId: string;
  currentProgress?: StreamProgressDto;
}

export type ChatAction =
  | { type: 'ADD_MESSAGE'; payload: ChatMessage }
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_TYPING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'SET_PROGRESS'; payload: StreamProgressDto | undefined }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'RESET_STATE' };

// WebSocket Connection Status
export enum ConnectionStatus {
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

// UI Component Props Types
export interface MessageBubbleProps {
  message: ChatMessage;
  isUser: boolean;
}

export interface MessageInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export interface ChartRendererProps {
  chartData: ChartData;
  className?: string;
}

export interface CitationCardProps {
  citations: Citation[];
  className?: string;
}

export interface TypingIndicatorProps {
  isVisible: boolean;
  progress?: StreamProgressDto;
}

// Utility Types
export type MessageWithoutId = Omit<ChatMessage, 'id'>;

export interface ErrorInfo {
  message: string;
  code?: string;
  recoverable?: boolean;
}