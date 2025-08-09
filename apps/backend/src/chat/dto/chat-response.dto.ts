import { ApiProperty } from '@nestjs/swagger';

export enum MessageType {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system',
  ERROR = 'error'
}

export class Citation {
  @ApiProperty({ description: 'Document ID or filename' })
  documentId: string;

  @ApiProperty({ description: 'Document title' })
  title: string;

  @ApiProperty({ description: 'Relevant excerpt from the document' })
  excerpt: string;

  @ApiProperty({ description: 'Page or section number', required: false })
  page?: number;
}

export class ChartData {
  @ApiProperty({ description: 'Chart type (bar, line, pie, scatter)' })
  type: 'bar' | 'line' | 'pie' | 'scatter';

  @ApiProperty({ description: 'Chart data' })
  data: any;

  @ApiProperty({ description: 'Chart options', required: false })
  options?: any;
}

export class ChatResponseDto {
  @ApiProperty({ description: 'The response message' })
  message: string;

  @ApiProperty({ enum: MessageType, description: 'Type of message' })
  type: MessageType;

  @ApiProperty({ description: 'Session ID for conversation tracking' })
  sessionId: string;

  @ApiProperty({ description: 'Timestamp of the response' })
  timestamp: Date;

  @ApiProperty({ type: [Citation], description: 'Document citations', required: false })
  citations?: Citation[];

  @ApiProperty({ type: ChartData, description: 'Visualization data', required: false })
  chartData?: ChartData;

  @ApiProperty({ description: 'Whether response supports streaming', required: false })
  streamable?: boolean;

  @ApiProperty({ description: 'Additional metadata', required: false })
  metadata?: Record<string, any>;
}