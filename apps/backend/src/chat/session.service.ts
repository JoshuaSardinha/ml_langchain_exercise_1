import { Injectable, Logger } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import { CHAT_CONSTANTS } from './chat.constants';

export interface Session {
  id: string;
  clientId: string;
  roomId: string;
  messages: SessionMessage[];
  createdAt: Date;
  lastActivity: Date;
  metadata: Record<string, any>;
}

export interface SessionMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface RateLimitInfo {
  messageCount: number;
  firstMessageTime: number;
  lastMessageTime: number;
}

@Injectable()
export class SessionService {
  private readonly logger = new Logger(SessionService.name);
  private sessions: Map<string, Session> = new Map();
  private clientSessions: Map<string, Set<string>> = new Map();
  private rateLimits: Map<string, RateLimitInfo> = new Map();
  private cleanupInterval: NodeJS.Timeout;

  constructor() {
    this.startSessionCleanup();
  }

  createSession(clientId: string, metadata: Record<string, any> = {}): Session {
    const existingSessionCount = this.clientSessions.get(clientId)?.size || 0;
    
    if (existingSessionCount >= CHAT_CONSTANTS.SESSION.MAX_SESSIONS_PER_CLIENT) {
      this.cleanupOldestSession(clientId);
    }

    const sessionId = uuidv4();
    const roomId = `room_${sessionId}`;
    
    const session: Session = {
      id: sessionId,
      clientId,
      roomId,
      messages: [],
      createdAt: new Date(),
      lastActivity: new Date(),
      metadata,
    };

    this.sessions.set(sessionId, session);
    
    if (!this.clientSessions.has(clientId)) {
      this.clientSessions.set(clientId, new Set());
    }
    this.clientSessions.get(clientId).add(sessionId);

    this.logger.log(`Created session ${sessionId} for client ${clientId}`);
    return session;
  }

  getSession(sessionId: string): Session | undefined {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.lastActivity = new Date();
    }
    return session;
  }

  updateSession(sessionId: string, updates: Partial<Session>): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      Object.assign(session, updates, { lastActivity: new Date() });
    }
  }

  addMessage(sessionId: string, message: SessionMessage): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      session.messages.push(message);
      session.lastActivity = new Date();
      
      if (session.messages.length > CHAT_CONSTANTS.SESSION.MAX_HISTORY_SIZE) {
        session.messages = session.messages.slice(-CHAT_CONSTANTS.SESSION.MAX_HISTORY_SIZE);
      }
    }
  }

  deleteSession(sessionId: string): void {
    const session = this.sessions.get(sessionId);
    if (session) {
      this.sessions.delete(sessionId);
      const clientSessions = this.clientSessions.get(session.clientId);
      if (clientSessions) {
        clientSessions.delete(sessionId);
        if (clientSessions.size === 0) {
          this.clientSessions.delete(session.clientId);
        }
      }
      this.logger.log(`Deleted session ${sessionId}`);
    }
  }

  getClientSessions(clientId: string): Session[] {
    const sessionIds = this.clientSessions.get(clientId);
    if (!sessionIds) return [];
    
    return Array.from(sessionIds)
      .map(id => this.sessions.get(id))
      .filter(session => session !== undefined) as Session[];
  }

  checkRateLimit(clientId: string): boolean {
    const now = Date.now();
    const rateLimit = this.rateLimits.get(clientId);

    if (!rateLimit) {
      this.rateLimits.set(clientId, {
        messageCount: 1,
        firstMessageTime: now,
        lastMessageTime: now,
      });
      return true;
    }

    const timeSinceFirst = now - rateLimit.firstMessageTime;
    const timeSinceLast = now - rateLimit.lastMessageTime;

    if (timeSinceLast < CHAT_CONSTANTS.RATE_LIMIT.COOLDOWN_PERIOD_MS) {
      return false;
    }

    if (timeSinceFirst > 60000) {
      this.rateLimits.set(clientId, {
        messageCount: 1,
        firstMessageTime: now,
        lastMessageTime: now,
      });
      return true;
    }

    if (rateLimit.messageCount >= CHAT_CONSTANTS.RATE_LIMIT.MAX_MESSAGES_PER_MINUTE) {
      return false;
    }

    rateLimit.messageCount++;
    rateLimit.lastMessageTime = now;
    return true;
  }

  private cleanupOldestSession(clientId: string): void {
    const sessions = this.getClientSessions(clientId);
    if (sessions.length > 0) {
      const oldestSession = sessions.reduce((oldest, current) => 
        oldest.lastActivity < current.lastActivity ? oldest : current
      );
      this.deleteSession(oldestSession.id);
    }
  }

  private startSessionCleanup(): void {
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      const expiredSessions: string[] = [];

      this.sessions.forEach((session, sessionId) => {
        const sessionAge = now - session.lastActivity.getTime();
        if (sessionAge > CHAT_CONSTANTS.SESSION.SESSION_TIMEOUT_MS) {
          expiredSessions.push(sessionId);
        }
      });

      expiredSessions.forEach(sessionId => {
        this.deleteSession(sessionId);
      });

      if (expiredSessions.length > 0) {
        this.logger.log(`Cleaned up ${expiredSessions.length} expired sessions`);
      }

      this.rateLimits.forEach((rateLimit, clientId) => {
        const timeSinceFirst = now - rateLimit.firstMessageTime;
        if (timeSinceFirst > 3600000) {
          this.rateLimits.delete(clientId);
        }
      });
    }, CHAT_CONSTANTS.SESSION.SESSION_CLEANUP_INTERVAL_MS);
  }

  onModuleDestroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
    }
  }
}