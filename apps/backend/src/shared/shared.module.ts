import { Module, Global } from '@nestjs/common';
import { HttpExceptionFilter } from './filters/http-exception.filter';
import { LoggingInterceptor } from './interceptors/logging.interceptor';

@Global()
@Module({
  providers: [HttpExceptionFilter, LoggingInterceptor],
  exports: [HttpExceptionFilter, LoggingInterceptor],
})
export class SharedModule {}