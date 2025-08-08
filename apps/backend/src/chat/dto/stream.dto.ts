import { ApiProperty } from '@nestjs/swagger';
import { IsString, IsNumber, IsOptional, IsObject, IsEnum, IsDateString } from 'class-validator';

export enum StreamStage {
  ANALYZING = 'analyzing',
  QUERYING = 'querying',
  PROCESSING = 'processing',
  GENERATING = 'generating',
  COMPLETE = 'complete',
  ERROR = 'error',
}

export class StreamProgressDto {
  @ApiProperty({ enum: StreamStage, description: 'Current processing stage' })
  @IsEnum(StreamStage)
  stage: StreamStage;

  @ApiProperty({ description: 'Progress percentage (0-100)', minimum: 0, maximum: 100 })
  @IsNumber()
  progress: number;

  @ApiProperty({ description: 'Human-readable progress message' })
  @IsString()
  message: string;

  @ApiProperty({ description: 'Optional metadata for the progress update', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}

export class StreamStartDto {
  @ApiProperty({ description: 'Unique identifier for the stream' })
  @IsString()
  streamId: string;

  @ApiProperty({ description: 'Total number of chunks expected' })
  @IsNumber()
  totalChunks: number;

  @ApiProperty({ description: 'Timestamp when streaming started' })
  @IsDateString()
  timestamp: Date;
}

export class StreamChunkDto {
  @ApiProperty({ description: 'Stream identifier' })
  @IsString()
  streamId: string;

  @ApiProperty({ description: 'Content chunk' })
  @IsString()
  chunk: string;

  @ApiProperty({ description: 'Chunk index in the sequence' })
  @IsNumber()
  index: number;

  @ApiProperty({ description: 'Timestamp of the chunk' })
  @IsDateString()
  timestamp: Date;

  @ApiProperty({ description: 'Optional chunk metadata', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}

export class StreamEndDto {
  @ApiProperty({ description: 'Stream identifier' })
  @IsString()
  streamId: string;

  @ApiProperty({ description: 'Complete response object' })
  @IsObject()
  fullResponse: any;

  @ApiProperty({ description: 'Timestamp when streaming ended' })
  @IsDateString()
  timestamp: Date;

  @ApiProperty({ description: 'Stream completion metadata', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}

export class RoomJoinDto {
  @ApiProperty({ description: 'Session ID to join (optional for new session)', required: false })
  @IsString()
  @IsOptional()
  sessionId?: string;

  @ApiProperty({ description: 'Additional metadata for room joining', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}

export class RoomJoinedDto {
  @ApiProperty({ description: 'Session ID' })
  @IsString()
  sessionId: string;

  @ApiProperty({ description: 'Room ID' })
  @IsString()
  roomId: string;

  @ApiProperty({ description: 'Chat history', type: [Object] })
  history: any[];

  @ApiProperty({ description: 'Room metadata', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}

export class TypingIndicatorDto {
  @ApiProperty({ description: 'Whether typing is in progress' })
  isTyping: boolean;

  @ApiProperty({ description: 'Client ID who is typing', required: false })
  @IsString()
  @IsOptional()
  clientId?: string;

  @ApiProperty({ description: 'Timestamp of typing event' })
  @IsDateString()
  timestamp: Date;
}

export class WebSocketErrorDto {
  @ApiProperty({ description: 'Error message' })
  @IsString()
  message: string;

  @ApiProperty({ description: 'Error code', required: false })
  @IsString()
  @IsOptional()
  code?: string;

  @ApiProperty({ description: 'Whether the error is recoverable', required: false })
  @IsOptional()
  recoverable?: boolean;

  @ApiProperty({ description: 'Timestamp of the error' })
  @IsDateString()
  timestamp: Date;

  @ApiProperty({ description: 'Additional error metadata', required: false })
  @IsObject()
  @IsOptional()
  metadata?: Record<string, any>;
}