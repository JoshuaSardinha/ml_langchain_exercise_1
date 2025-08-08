import { Injectable, Logger } from '@nestjs/common';
import { ChatMessageDto, ChatResponseDto, MessageType } from './dto';
import { MLService } from '../ml/ml.service';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class ChatService {
  private readonly logger = new Logger(ChatService.name);
  private sessions: Map<string, any[]> = new Map();

  constructor(private readonly mlService: MLService) {}

  async processMessage(chatMessage: ChatMessageDto): Promise<ChatResponseDto> {
    const sessionId = chatMessage.sessionId || uuidv4();
    
    if (!this.sessions.has(sessionId)) {
      this.sessions.set(sessionId, []);
    }

    const sessionHistory = this.sessions.get(sessionId);
    sessionHistory.push({
      type: MessageType.USER,
      message: chatMessage.message,
      timestamp: new Date()
    });

    try {
      this.logger.log(`Processing message for session ${sessionId}`);
      
      const mlResponse = await this.mlService.sendToMLService({
        message: chatMessage.message,
        sessionId,
        context: chatMessage.context,
        history: sessionHistory
      });

      const response: ChatResponseDto = {
        message: mlResponse.message,
        type: MessageType.ASSISTANT,
        sessionId,
        timestamp: new Date(),
        citations: mlResponse.citations,
        chartData: mlResponse.chartData,
        metadata: mlResponse.metadata
      };

      sessionHistory.push({
        type: MessageType.ASSISTANT,
        message: response.message,
        timestamp: response.timestamp
      });

      if (sessionHistory.length > 20) {
        sessionHistory.shift();
        sessionHistory.shift();
      }

      return response;
    } catch (error) {
      this.logger.error(`Error processing message: ${error.message}`, error.stack);
      
      return {
        message: 'I apologize, but I encountered an error processing your request. Please try again.',
        type: MessageType.ERROR,
        sessionId,
        timestamp: new Date()
      };
    }
  }

  getSessionHistory(sessionId: string): any[] {
    return this.sessions.get(sessionId) || [];
  }

  clearSession(sessionId: string): void {
    this.sessions.delete(sessionId);
  }
}