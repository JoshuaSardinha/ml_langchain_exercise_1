import { IsString, IsNotEmpty, IsOptional, IsObject } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class ChatMessageDto {
  @ApiProperty({ description: 'The message content from the user' })
  @IsString()
  @IsNotEmpty()
  message: string;

  @ApiProperty({ description: 'Optional session ID for conversation continuity', required: false })
  @IsString()
  @IsOptional()
  sessionId?: string;

  @ApiProperty({ description: 'Optional context data for the message', required: false })
  @IsObject()
  @IsOptional()
  context?: Record<string, any>;
}