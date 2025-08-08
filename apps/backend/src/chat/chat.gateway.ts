import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  MessageBody,
  ConnectedSocket,
  OnGatewayConnection,
  OnGatewayDisconnect,
  OnGatewayInit,
  WsException,
} from '@nestjs/websockets';
import { Logger, UseGuards } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { ChatService } from './chat.service';
import { SessionService } from './session.service';
import { ChatMessageDto, StreamProgressDto } from './dto';
import { WEBSOCKET_EVENTS, ERROR_MESSAGES, CHAT_CONSTANTS } from './chat.constants';

interface ClientInfo {
  clientId: string;
  sessionId?: string;
  roomId?: string;
  ipAddress: string;
  connectedAt: Date;
  lastActivity: Date;
}

@WebSocketGateway({
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:4200',
    credentials: true,
  },
  namespace: '/chat',
  transports: ['websocket', 'polling'],
})
export class ChatGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(ChatGateway.name);
  private connectedClients = new Map<string, ClientInfo>();
  private activeStreams = new Map<string, NodeJS.Timeout>();
  private ipConnectionCount = new Map<string, number>();

  constructor(
    private readonly chatService: ChatService,
    private readonly sessionService: SessionService,
  ) {}

  afterInit(server: Server) {
    this.logger.log('WebSocket Gateway initialized');
    this.setupHeartbeat();
  }

  handleConnection(client: Socket) {
    const ipAddress = this.getClientIp(client);
    
    if (!this.checkConnectionLimit(ipAddress)) {
      client.emit(WEBSOCKET_EVENTS.ERROR, {
        message: ERROR_MESSAGES.CONNECTION_LIMIT_REACHED,
      });
      client.disconnect();
      return;
    }

    const clientInfo: ClientInfo = {
      clientId: client.id,
      ipAddress,
      connectedAt: new Date(),
      lastActivity: new Date(),
    };

    this.connectedClients.set(client.id, clientInfo);
    this.incrementIpConnectionCount(ipAddress);
    
    this.logger.log(`Client connected: ${client.id} from ${ipAddress}`);
    
    client.emit(WEBSOCKET_EVENTS.CONNECTED, {
      message: 'Connected to Data Doctor chat server',
      clientId: client.id,
      timestamp: new Date(),
    });
  }

  handleDisconnect(client: Socket) {
    const clientInfo = this.connectedClients.get(client.id);
    
    if (clientInfo) {
      if (clientInfo.roomId) {
        client.leave(clientInfo.roomId);
      }
      
      if (clientInfo.sessionId) {
        this.sessionService.updateSession(clientInfo.sessionId, {
          metadata: { lastDisconnect: new Date() },
        });
      }
      
      this.decrementIpConnectionCount(clientInfo.ipAddress);
      this.cancelActiveStream(client.id);
    }
    
    this.connectedClients.delete(client.id);
    this.logger.log(`Client disconnected: ${client.id}`);
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.JOIN_ROOM)
  async handleJoinRoom(
    @ConnectedSocket() client: Socket,
    @MessageBody() data: { sessionId?: string },
  ) {
    const clientInfo = this.connectedClients.get(client.id);
    if (!clientInfo) return;

    let session;
    
    if (data.sessionId) {
      session = this.sessionService.getSession(data.sessionId);
      if (!session) {
        client.emit(WEBSOCKET_EVENTS.ERROR, {
          message: ERROR_MESSAGES.SESSION_NOT_FOUND,
        });
        return;
      }
    } else {
      session = this.sessionService.createSession(client.id);
    }

    if (clientInfo.roomId) {
      await client.leave(clientInfo.roomId);
    }

    await client.join(session.roomId);
    
    clientInfo.sessionId = session.id;
    clientInfo.roomId = session.roomId;
    clientInfo.lastActivity = new Date();

    client.emit(WEBSOCKET_EVENTS.ROOM_JOINED, {
      sessionId: session.id,
      roomId: session.roomId,
      history: session.messages,
    });

    this.logger.log(`Client ${client.id} joined room ${session.roomId}`);
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.MESSAGE)
  async handleMessage(
    @MessageBody() data: ChatMessageDto,
    @ConnectedSocket() client: Socket,
  ) {
    const clientInfo = this.connectedClients.get(client.id);
    if (!clientInfo) {
      throw new WsException(ERROR_MESSAGES.AUTHENTICATION_FAILED);
    }

    if (!this.sessionService.checkRateLimit(client.id)) {
      client.emit(WEBSOCKET_EVENTS.ERROR, {
        message: ERROR_MESSAGES.RATE_LIMIT_EXCEEDED,
      });
      return;
    }

    if (data.message.length > CHAT_CONSTANTS.RATE_LIMIT.MESSAGE_MAX_LENGTH) {
      client.emit(WEBSOCKET_EVENTS.ERROR, {
        message: ERROR_MESSAGES.MESSAGE_TOO_LONG,
      });
      return;
    }

    clientInfo.lastActivity = new Date();
    
    if (!clientInfo.sessionId) {
      const session = this.sessionService.createSession(client.id);
      clientInfo.sessionId = session.id;
      clientInfo.roomId = session.roomId;
      await client.join(session.roomId);
    }

    this.logger.log(`Message received from ${client.id}: ${data.message.substring(0, 100)}...`);
    
    this.server.to(clientInfo.roomId).emit(WEBSOCKET_EVENTS.TYPING, { isTyping: true });
    
    try {
      const response = await this.chatService.processMessage({
        ...data,
        sessionId: clientInfo.sessionId,
      }, {
        streaming: data.context?.streaming || false,
        onProgress: (progress: StreamProgressDto) => {
          client.emit(WEBSOCKET_EVENTS.PROGRESS_UPDATE, progress);
        },
      });
      
      this.server.to(clientInfo.roomId).emit(WEBSOCKET_EVENTS.TYPING, { isTyping: false });
      
      if (data.context?.streaming && response.streamable) {
        await this.streamResponse(client, response, clientInfo.roomId);
      } else {
        this.server.to(clientInfo.roomId).emit(WEBSOCKET_EVENTS.RESPONSE, response);
      }
      
      return response;
    } catch (error) {
      this.logger.error(`Error handling message: ${error.message}`, error.stack);
      
      this.server.to(clientInfo.roomId).emit(WEBSOCKET_EVENTS.TYPING, { isTyping: false });
      
      client.emit(WEBSOCKET_EVENTS.ERROR, {
        message: ERROR_MESSAGES.ML_SERVICE_UNAVAILABLE,
        error: error.message,
      });
    }
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.TYPING)
  handleTyping(@ConnectedSocket() client: Socket, @MessageBody() data: { isTyping: boolean }) {
    const clientInfo = this.connectedClients.get(client.id);
    if (clientInfo?.roomId) {
      client.to(clientInfo.roomId).emit(WEBSOCKET_EVENTS.USER_TYPING, {
        clientId: client.id,
        isTyping: data.isTyping,
      });
    }
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.CLEAR_SESSION)
  handleClearSession(@ConnectedSocket() client: Socket, @MessageBody() data: { sessionId: string }) {
    const clientInfo = this.connectedClients.get(client.id);
    if (!clientInfo || clientInfo.sessionId !== data.sessionId) {
      client.emit(WEBSOCKET_EVENTS.ERROR, {
        message: ERROR_MESSAGES.SESSION_NOT_FOUND,
      });
      return;
    }

    this.sessionService.deleteSession(data.sessionId);
    
    if (clientInfo.roomId) {
      client.leave(clientInfo.roomId);
    }
    
    clientInfo.sessionId = undefined;
    clientInfo.roomId = undefined;
    
    client.emit(WEBSOCKET_EVENTS.SESSION_CLEARED, { 
      message: 'Session cleared successfully',
      timestamp: new Date(),
    });
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.CANCEL_REQUEST)
  handleCancelRequest(@ConnectedSocket() client: Socket) {
    this.cancelActiveStream(client.id);
    client.emit(WEBSOCKET_EVENTS.REQUEST_CANCELLED, {
      message: 'Request cancelled',
      timestamp: new Date(),
    });
  }

  @SubscribeMessage(WEBSOCKET_EVENTS.HEARTBEAT)
  handleHeartbeat(@ConnectedSocket() client: Socket) {
    const clientInfo = this.connectedClients.get(client.id);
    if (clientInfo) {
      clientInfo.lastActivity = new Date();
    }
    client.emit(WEBSOCKET_EVENTS.PONG, { timestamp: new Date() });
  }

  private async streamResponse(client: Socket, response: any, roomId: string) {
    const streamId = `${client.id}_${Date.now()}`;
    const chunks = this.chunkResponse(response.message);
    let chunkIndex = 0;

    client.emit(WEBSOCKET_EVENTS.STREAM_START, {
      streamId,
      totalChunks: chunks.length,
      timestamp: new Date(),
    });

    const streamInterval = setInterval(() => {
      if (chunkIndex >= chunks.length) {
        clearInterval(streamInterval);
        this.activeStreams.delete(client.id);
        
        this.server.to(roomId).emit(WEBSOCKET_EVENTS.STREAM_END, {
          streamId,
          fullResponse: response,
          timestamp: new Date(),
        });
        return;
      }

      client.emit(WEBSOCKET_EVENTS.STREAM_CHUNK, {
        streamId,
        chunk: chunks[chunkIndex],
        index: chunkIndex,
        timestamp: new Date(),
      });

      chunkIndex++;
    }, CHAT_CONSTANTS.STREAMING.CHUNK_DELAY_MS);

    this.activeStreams.set(client.id, streamInterval);

    setTimeout(() => {
      this.cancelActiveStream(client.id);
    }, CHAT_CONSTANTS.STREAMING.MAX_STREAM_DURATION_MS);
  }

  private chunkResponse(message: string): string[] {
    const chunks: string[] = [];
    const chunkSize = CHAT_CONSTANTS.STREAMING.CHUNK_SIZE;
    
    for (let i = 0; i < message.length; i += chunkSize) {
      chunks.push(message.slice(i, i + chunkSize));
    }
    
    return chunks;
  }

  private cancelActiveStream(clientId: string) {
    const stream = this.activeStreams.get(clientId);
    if (stream) {
      clearInterval(stream);
      this.activeStreams.delete(clientId);
    }
  }

  private getClientIp(client: Socket): string {
    return client.handshake.headers['x-forwarded-for']?.toString().split(',')[0].trim() ||
           client.handshake.address ||
           '127.0.0.1';
  }

  private checkConnectionLimit(ipAddress: string): boolean {
    const count = this.ipConnectionCount.get(ipAddress) || 0;
    return count < CHAT_CONSTANTS.WEBSOCKET.MAX_CONNECTIONS_PER_IP;
  }

  private incrementIpConnectionCount(ipAddress: string) {
    const count = this.ipConnectionCount.get(ipAddress) || 0;
    this.ipConnectionCount.set(ipAddress, count + 1);
  }

  private decrementIpConnectionCount(ipAddress: string) {
    const count = this.ipConnectionCount.get(ipAddress) || 0;
    if (count > 1) {
      this.ipConnectionCount.set(ipAddress, count - 1);
    } else {
      this.ipConnectionCount.delete(ipAddress);
    }
  }

  private setupHeartbeat() {
    setInterval(() => {
      const now = Date.now();
      
      this.connectedClients.forEach((clientInfo, clientId) => {
        const timeSinceLastActivity = now - clientInfo.lastActivity.getTime();
        
        if (timeSinceLastActivity > CHAT_CONSTANTS.WEBSOCKET.HEARTBEAT_TIMEOUT_MS) {
          const client = this.server.sockets.sockets.get(clientId);
          if (client) {
            this.logger.warn(`Disconnecting inactive client: ${clientId}`);
            client.disconnect();
          }
        }
      });
    }, CHAT_CONSTANTS.WEBSOCKET.HEARTBEAT_INTERVAL_MS);
  }
}