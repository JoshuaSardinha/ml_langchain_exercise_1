/**
 * Data Doctor Backend API Server
 * NestJS backend with WebSocket support for real-time chat
 */

import { Logger, ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import { ConfigService } from '@nestjs/config';
import { AppModule } from './app/app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  const configService = app.get(ConfigService);
  
  const globalPrefix = configService.get('API_PREFIX', 'api');
  const apiVersion = configService.get('API_VERSION', 'v1');
  app.setGlobalPrefix(`${globalPrefix}/${apiVersion}`);
  
  app.enableCors({
    origin: configService.get('FRONTEND_URL', 'http://localhost:4200'),
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  });
  
  app.useGlobalPipes(
    new ValidationPipe({
      transform: true,
      whitelist: true,
      forbidNonWhitelisted: true,
      transformOptions: {
        enableImplicitConversion: true,
      },
    }),
  );
  
  const config = new DocumentBuilder()
    .setTitle('Data Doctor API')
    .setDescription('AI Health Assistant Backend API')
    .setVersion('1.0')
    .addTag('chat', 'Chat operations')
    .addTag('health', 'Health check')
    .build();
  
  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup(`${globalPrefix}/${apiVersion}/docs`, app, document);
  
  const port = configService.get('PORT', 3000);
  await app.listen(port);
  
  Logger.log(
    `🚀 Application is running on: http://localhost:${port}/${globalPrefix}/${apiVersion}`
  );
  Logger.log(
    `📚 API Documentation available at: http://localhost:${port}/${globalPrefix}/${apiVersion}/docs`
  );
  Logger.log(
    `🔌 WebSocket server is running on namespace: /chat`
  );
}

bootstrap();
