import { Module } from '@nestjs/common';
import { ChatController } from './chat.controller';
import { ChatService } from './chat.service';
import { ChatGateway } from './chat.gateway';
import { SessionService } from './session.service';
import { MLModule } from '../ml/ml.module';

@Module({
  imports: [MLModule],
  controllers: [ChatController],
  providers: [ChatService, SessionService, ChatGateway],
  exports: [ChatService, SessionService],
})
export class ChatModule {}