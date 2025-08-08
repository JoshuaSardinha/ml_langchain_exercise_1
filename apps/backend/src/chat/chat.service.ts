import { Injectable, Logger } from '@nestjs/common';
import { ChatMessageDto, ChatResponseDto, MessageType, StreamProgressDto } from './dto';
import { SessionService, SessionMessage } from './session.service';
import { MLService } from '../ml/ml.service';
import { CHAT_CONSTANTS } from './chat.constants';
import { v4 as uuidv4 } from 'uuid';

interface ProcessingOptions {
  streaming?: boolean;
  onProgress?: (progress: StreamProgressDto) => void;
}

interface MessageQueue {
  id: string;
  message: ChatMessageDto;
  options: ProcessingOptions;
  timestamp: Date;
  retryCount: number;
  resolve: (value: ChatResponseDto) => void;
  reject: (error: Error) => void;
}

@Injectable()
export class ChatService {
  private readonly logger = new Logger(ChatService.name);
  private messageQueue: MessageQueue[] = [];
  private processingQueue = new Set<string>();
  private isProcessing = false;

  constructor(
    private readonly mlService: MLService,
    private readonly sessionService: SessionService,
  ) {
    this.startQueueProcessor();
  }

  async processMessage(
    chatMessage: ChatMessageDto,
    options: ProcessingOptions = {},
  ): Promise<ChatResponseDto> {
    const sessionId = chatMessage.sessionId || uuidv4();
    
    return new Promise((resolve, reject) => {
      if (this.messageQueue.length >= CHAT_CONSTANTS.QUEUE.MAX_QUEUE_SIZE) {
        reject(new Error('Message queue is full. Please try again later.'));
        return;
      }

      const queueItem: MessageQueue = {
        id: uuidv4(),
        message: { ...chatMessage, sessionId },
        options,
        timestamp: new Date(),
        retryCount: 0,
        resolve,
        reject,
      };

      this.messageQueue.push(queueItem);
      this.processQueue();
    });
  }

  private async processQueue() {
    if (this.isProcessing || this.messageQueue.length === 0) {
      return;
    }

    this.isProcessing = true;

    while (this.messageQueue.length > 0) {
      const item = this.messageQueue.shift();
      if (!item) break;

      const timeoutId = setTimeout(() => {
        this.handleTimeout(item);
      }, CHAT_CONSTANTS.QUEUE.PROCESSING_TIMEOUT_MS);

      try {
        const result = await this.processMessageInternal(item.message, item.options);
        clearTimeout(timeoutId);
        item.resolve(result);
      } catch (error) {
        clearTimeout(timeoutId);
        await this.handleProcessingError(item, error);
      }
    }

    this.isProcessing = false;
  }

  private async processMessageInternal(
    chatMessage: ChatMessageDto,
    options: ProcessingOptions,
  ): Promise<ChatResponseDto> {
    const { sessionId } = chatMessage;
    let session = this.sessionService.getSession(sessionId);

    if (!session) {
      session = this.sessionService.createSession(sessionId, {
        createdFrom: 'chat-service',
      });
    }

    const userMessage: SessionMessage = {
      id: uuidv4(),
      type: 'user',
      content: chatMessage.message,
      timestamp: new Date(),
      metadata: chatMessage.context,
    };

    this.sessionService.addMessage(sessionId, userMessage);

    try {
      this.logger.log(`Processing message for session ${sessionId}`);

      if (options.onProgress) {
        options.onProgress({
          stage: 'analyzing',
          progress: 25,
          message: 'Analyzing your message...',
        });
      }

      const mlResponse = await this.mlService.sendToMLService({
        message: chatMessage.message,
        sessionId,
        context: chatMessage.context,
        history: session.messages.map(msg => ({
          type: msg.type,
          message: msg.content,
          timestamp: msg.timestamp,
        })),
      });

      if (options.onProgress) {
        options.onProgress({
          stage: 'processing',
          progress: 75,
          message: 'Processing ML response...',
        });
      }

      const response: ChatResponseDto = {
        message: mlResponse.message,
        type: MessageType.ASSISTANT,
        sessionId,
        timestamp: new Date(),
        citations: mlResponse.citations,
        chartData: mlResponse.chartData,
        metadata: {
          ...mlResponse.metadata,
          processingTime: Date.now() - userMessage.timestamp.getTime(),
          streamable: options.streaming && mlResponse.message.length > 500,
        },
      };

      const assistantMessage: SessionMessage = {
        id: uuidv4(),
        type: 'assistant',
        content: response.message,
        timestamp: response.timestamp,
        metadata: {
          citations: response.citations,
          chartData: response.chartData,
          ...response.metadata,
        },
      };

      this.sessionService.addMessage(sessionId, assistantMessage);

      if (options.onProgress) {
        options.onProgress({
          stage: 'complete',
          progress: 100,
          message: 'Response ready!',
        });
      }

      return response;
    } catch (error) {
      this.logger.error(`Error processing message: ${error.message}`, error.stack);

      const errorMessage: SessionMessage = {
        id: uuidv4(),
        type: 'system',
        content: `Error: ${error.message}`,
        timestamp: new Date(),
        metadata: { error: true },
      };

      this.sessionService.addMessage(sessionId, errorMessage);

      return {
        message: this.getErrorMessage(error),
        type: MessageType.ERROR,
        sessionId,
        timestamp: new Date(),
        metadata: {
          error: error.message,
          recoverable: this.isRecoverableError(error),
        },
      };
    }
  }

  private async handleProcessingError(item: MessageQueue, error: any) {
    if (item.retryCount < CHAT_CONSTANTS.QUEUE.MAX_RETRIES && this.isRecoverableError(error)) {
      item.retryCount++;
      
      setTimeout(() => {
        this.messageQueue.unshift(item);
        this.processQueue();
      }, CHAT_CONSTANTS.QUEUE.RETRY_DELAY_MS * item.retryCount);

      this.logger.warn(
        `Retrying message processing (attempt ${item.retryCount + 1}/${
          CHAT_CONSTANTS.QUEUE.MAX_RETRIES + 1
        }) for session ${item.message.sessionId}`,
      );
    } else {
      item.reject(error);
    }
  }

  private handleTimeout(item: MessageQueue) {
    const error = new Error('Processing timeout exceeded');
    item.reject(error);
    this.logger.error(`Processing timeout for session ${item.message.sessionId}`);
  }

  private isRecoverableError(error: any): boolean {
    if (typeof error === 'string') return true;
    
    const recoverableCodes = [
      'ECONNRESET',
      'ETIMEDOUT',
      'ENOTFOUND',
      'SERVICE_UNAVAILABLE',
    ];
    
    return recoverableCodes.some(code => 
      error.code === code || error.message?.includes(code)
    );
  }

  private getErrorMessage(error: any): string {
    if (error.message?.includes('timeout')) {
      return 'The request took too long to process. Please try again with a simpler query.';
    }
    
    if (error.message?.includes('service unavailable')) {
      return 'The AI service is temporarily unavailable. Please try again in a moment.';
    }
    
    if (this.isRecoverableError(error)) {
      return 'I encountered a temporary issue. Please try again.';
    }
    
    return 'I apologize, but I encountered an error processing your request. Please try rephrasing your question.';
  }

  private startQueueProcessor() {
    setInterval(() => {
      if (!this.isProcessing && this.messageQueue.length > 0) {
        this.processQueue();
      }
    }, 100);
  }

  getSessionHistory(sessionId: string): SessionMessage[] {
    const session = this.sessionService.getSession(sessionId);
    return session ? session.messages : [];
  }

  clearSession(sessionId: string): void {
    this.sessionService.deleteSession(sessionId);
    this.logger.log(`Session ${sessionId} cleared`);
  }

  getQueueStatus() {
    return {
      queueLength: this.messageQueue.length,
      processing: this.isProcessing,
      processingItems: this.processingQueue.size,
    };
  }

  cancelMessage(messageId: string): boolean {
    const index = this.messageQueue.findIndex(item => item.id === messageId);
    if (index >= 0) {
      const item = this.messageQueue.splice(index, 1)[0];
      item.reject(new Error('Message cancelled by user'));
      return true;
    }
    return false;
  }
}