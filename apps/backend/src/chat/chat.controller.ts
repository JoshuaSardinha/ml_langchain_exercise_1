import { Controller, Post, Body, Get, Param, Delete, ValidationPipe } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse } from '@nestjs/swagger';
import { ChatService } from './chat.service';
import { ChatMessageDto, ChatResponseDto } from './dto';

@ApiTags('chat')
@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post('message')
  @ApiOperation({ summary: 'Send a chat message' })
  @ApiResponse({ status: 200, description: 'Message processed successfully', type: ChatResponseDto })
  @ApiResponse({ status: 400, description: 'Invalid request' })
  async sendMessage(@Body(ValidationPipe) chatMessage: ChatMessageDto): Promise<ChatResponseDto> {
    return this.chatService.processMessage(chatMessage);
  }

  @Get('session/:sessionId/history')
  @ApiOperation({ summary: 'Get chat history for a session' })
  @ApiResponse({ status: 200, description: 'Chat history retrieved' })
  getSessionHistory(@Param('sessionId') sessionId: string) {
    return this.chatService.getSessionHistory(sessionId);
  }

  @Delete('session/:sessionId')
  @ApiOperation({ summary: 'Clear a chat session' })
  @ApiResponse({ status: 200, description: 'Session cleared' })
  clearSession(@Param('sessionId') sessionId: string) {
    this.chatService.clearSession(sessionId);
    return { message: 'Session cleared successfully' };
  }
}