import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
  Logger,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(LoggingInterceptor.name);

  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    const request = context.switchToHttp().getRequest();
    const { method, url, body } = request;
    const now = Date.now();

    this.logger.log(`Incoming request: ${method} ${url}`);
    
    if (body && Object.keys(body).length > 0) {
      this.logger.debug(`Request body: ${JSON.stringify(body)}`);
    }

    return next
      .handle()
      .pipe(
        tap({
          next: (data) => {
            const responseTime = Date.now() - now;
            this.logger.log(
              `Outgoing response: ${method} ${url} - ${responseTime}ms`,
            );
            
            if (data && typeof data === 'object' && data !== null && Object.keys(data).length < 10) {
              this.logger.debug(`Response data: ${JSON.stringify(data)}`);
            }
          },
          error: (error) => {
            const responseTime = Date.now() - now;
            this.logger.error(
              `Request failed: ${method} ${url} - ${responseTime}ms - ${error.message}`,
            );
          },
        }),
      );
  }
}