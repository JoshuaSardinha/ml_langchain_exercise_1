import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  MessageBody,
  ConnectedSocket,
  OnGatewayConnection,
  OnGatewayDisconnect,
  OnGatewayInit,
} from '@nestjs/websockets';
import { Logger } from '@nestjs/common';
import { Server, Socket } from 'socket.io';
import { ChatService } from './chat.service';
import { ChatMessageDto } from './dto';

@WebSocketGateway({
  cors: {
    origin: process.env.FRONTEND_URL || 'http://localhost:4200',
    credentials: true,
  },
  namespace: '/chat',
})
export class ChatGateway implements OnGatewayInit, OnGatewayConnection, OnGatewayDisconnect {
  @WebSocketServer()
  server: Server;

  private readonly logger = new Logger(ChatGateway.name);
  private connectedClients = new Map<string, string>();

  constructor(private readonly chatService: ChatService) {}

  afterInit(server: Server) {
    this.logger.log('WebSocket Gateway initialized');
  }

  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
    this.connectedClients.set(client.id, client.id);
    
    client.emit('connected', {
      message: 'Connected to Data Doctor chat server',
      clientId: client.id,
    });
  }

  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    this.connectedClients.delete(client.id);
  }

  @SubscribeMessage('message')
  async handleMessage(
    @MessageBody() data: ChatMessageDto,
    @ConnectedSocket() client: Socket,
  ) {
    this.logger.log(`Message received from ${client.id}: ${data.message}`);
    
    client.emit('typing', { isTyping: true });
    
    try {
      const response = await this.chatService.processMessage(data);
      
      client.emit('typing', { isTyping: false });
      
      client.emit('response', response);
      
      return response;
    } catch (error) {
      this.logger.error(`Error handling message: ${error.message}`, error.stack);
      
      client.emit('typing', { isTyping: false });
      
      client.emit('error', {
        message: 'Failed to process message',
        error: error.message,
      });
    }
  }

  @SubscribeMessage('typing')
  handleTyping(@ConnectedSocket() client: Socket, @MessageBody() data: { isTyping: boolean }) {
    client.broadcast.emit('userTyping', {
      clientId: client.id,
      isTyping: data.isTyping,
    });
  }

  @SubscribeMessage('clearSession')
  handleClearSession(@ConnectedSocket() client: Socket, @MessageBody() data: { sessionId: string }) {
    this.chatService.clearSession(data.sessionId);
    client.emit('sessionCleared', { message: 'Session cleared successfully' });
  }
}