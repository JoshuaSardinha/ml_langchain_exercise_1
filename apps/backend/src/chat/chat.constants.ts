export const CHAT_CONSTANTS = {
  RATE_LIMIT: {
    MAX_MESSAGES_PER_MINUTE: 20,
    MAX_MESSAGES_PER_HOUR: 100,
    MESSAGE_MAX_LENGTH: 5000,
    COOLDOWN_PERIOD_MS: 1000,
  },
  SESSION: {
    MAX_HISTORY_SIZE: 50,
    SESSION_TIMEOUT_MS: 30 * 60 * 1000,
    MAX_SESSIONS_PER_CLIENT: 5,
    SESSION_CLEANUP_INTERVAL_MS: 5 * 60 * 1000,
  },
  WEBSOCKET: {
    MAX_CONNECTIONS_PER_IP: 10,
    HEARTBEAT_INTERVAL_MS: 30000,
    HEARTBEAT_TIMEOUT_MS: 60000,
    RECONNECTION_ATTEMPTS: 3,
    RECONNECTION_DELAY_MS: 1000,
  },
  STREAMING: {
    CHUNK_SIZE: 100,
    CHUNK_DELAY_MS: 50,
    MAX_STREAM_DURATION_MS: 120000,
  },
  QUEUE: {
    MAX_QUEUE_SIZE: 100,
    PROCESSING_TIMEOUT_MS: 30000, // 30s timeout sufficient for both prediction and document search
    MAX_RETRIES: 3,
    RETRY_DELAY_MS: 2000,
  },
};

export const WEBSOCKET_EVENTS = {
  CONNECTION: 'connection',
  DISCONNECT: 'disconnect',
  MESSAGE: 'message',
  RESPONSE: 'response',
  TYPING: 'typing',
  USER_TYPING: 'userTyping',
  ERROR: 'error',
  CONNECTED: 'connected',
  SESSION_CLEARED: 'sessionCleared',
  CLEAR_SESSION: 'clearSession',
  JOIN_ROOM: 'joinRoom',
  LEAVE_ROOM: 'leaveRoom',
  ROOM_JOINED: 'roomJoined',
  STREAM_START: 'streamStart',
  STREAM_CHUNK: 'streamChunk',
  STREAM_END: 'streamEnd',
  PROGRESS_UPDATE: 'progressUpdate',
  CANCEL_REQUEST: 'cancelRequest',
  REQUEST_CANCELLED: 'requestCancelled',
  HEARTBEAT: 'heartbeat',
  PONG: 'pong',
} as const;

export const ERROR_MESSAGES = {
  RATE_LIMIT_EXCEEDED: 'Rate limit exceeded. Please slow down.',
  MESSAGE_TOO_LONG: 'Message exceeds maximum length.',
  SESSION_NOT_FOUND: 'Session not found or expired.',
  MAX_SESSIONS_REACHED: 'Maximum number of sessions reached.',
  CONNECTION_LIMIT_REACHED: 'Connection limit reached for this IP.',
  PROCESSING_TIMEOUT: 'Request processing timeout.',
  INVALID_MESSAGE_FORMAT: 'Invalid message format.',
  ML_SERVICE_UNAVAILABLE: 'ML service is temporarily unavailable.',
  AUTHENTICATION_FAILED: 'Authentication failed.',
  UNKNOWN_ERROR: 'An unknown error occurred.',
} as const;