import { Controller, Get } from '@nestjs/common';
import { AppService } from './app.service';
import { MLService } from '../ml/ml.service';

@Controller()
export class AppController {
  constructor(
    private readonly appService: AppService,
    private readonly mlService: MLService
  ) {}

  @Get()
  getData() {
    return this.appService.getData();
  }

  @Get('health')
  async getHealth() {
    const mlServiceHealthy = await this.mlService.checkHealth();
    return {
      status: 'healthy',
      service: 'backend',
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      dependencies: {
        mlService: mlServiceHealthy ? 'healthy' : 'unhealthy'
      }
    };
  }
}
