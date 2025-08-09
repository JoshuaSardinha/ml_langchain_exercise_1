import { HttpException, HttpStatus, Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosError, AxiosInstance } from 'axios';
import {
  MLDataQueryRequest,
  MLDataQueryResponse,
  MLDocumentSearchRequest,
  MLDocumentSearchResponse,
  MLPredictionRequest,
  MLPredictionResponse,
  MLRequest,
  MLResponse,
} from './interfaces/ml.interface';

@Injectable()
export class MLService {
  private readonly logger = new Logger(MLService.name);
  private readonly axiosInstance: AxiosInstance;
  private readonly mlServiceUrl: string;
  private readonly requestTimings = new Map<string, number>();

  constructor(private readonly configService: ConfigService) {
    this.mlServiceUrl = this.configService.get<string>(
      'ML_SERVICE_URL',
      'http://localhost:8000'
    );

    this.axiosInstance = axios.create({
      baseURL: this.mlServiceUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.axiosInstance.interceptors.request.use(
      (config) => {
        const requestId = `${config.method}_${
          config.url
        }_${Date.now()}_${Math.random()}`;
        this.requestTimings.set(requestId, Date.now());
        (config as any).requestId = requestId; // Store requestId for response tracking

        this.logger.log(
          `🚀 ML Service Request: ${config.method?.toUpperCase()} ${config.url}`
        );
        this.logger.debug(`Request params: ${JSON.stringify(config.params)}`);
        return config;
      },
      (error) => {
        this.logger.error('ML Service Request Error:', error.message);
        return Promise.reject(error);
      }
    );

    this.axiosInstance.interceptors.response.use(
      (response) => {
        const requestId = (response.config as any).requestId;
        const startTime = this.requestTimings.get(requestId) || Date.now();
        const duration = Date.now() - startTime;
        this.requestTimings.delete(requestId); // Cleanup

        this.logger.log(
          `✅ ML Service Response: ${response.status} ${response.config.url} (${duration}ms)`
        );
        this.logger.debug(
          `Response data keys: ${Object.keys(response.data || {}).join(', ')}`
        );
        return response;
      },
      (error) => {
        const requestId = (error.config as any)?.requestId;
        const startTime = this.requestTimings.get(requestId) || Date.now();
        const duration = Date.now() - startTime;
        if (requestId) this.requestTimings.delete(requestId); // Cleanup

        this.logger.error(
          `ML Service Error: ${error.response?.status || 'NETWORK'} ${
            error.config?.url
          } (${duration}ms)`
        );
        this.handleAxiosError(error);
        return Promise.reject(error);
      }
    );
  }

  async sendToMLService(request: MLRequest): Promise<MLResponse> {
    const maxRetries = 3;
    const baseDelay = 1000; // 1 second base delay

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        // ML service expects query parameters, not body data
        const params = {
          message: request.message,
          session_id: request.sessionId,
          user_id: request.context?.userId,
        };

        this.logger.log(
          `💬 Chat Request (attempt ${attempt}/${maxRetries}): "${request.message.substring(
            0,
            100
          )}..."`
        );
        const response = await this.axiosInstance.post('/api/v1/chat', null, {
          params,
        });

        // Log success
        this.logger.log(
          `✅ Chat Response Success: ${
            response.data.message?.length || 0
          } chars`
        );
        return response.data;
      } catch (error) {
        const isLastAttempt = attempt === maxRetries;
        const isRetryableError = this.isRetryableError(error);

        this.logger.error(
          `Chat Request Failed (attempt ${attempt}/${maxRetries}): ${error.message}`
        );

        if (!isLastAttempt && isRetryableError) {
          const delay = baseDelay * Math.pow(2, attempt - 1); // Exponential backoff
          this.logger.warn(`⏳ Retrying in ${delay}ms...`);
          await new Promise((resolve) => setTimeout(resolve, delay));
          continue;
        }

        // Final failure - throw with enhanced error message
        this.logger.error(
          `💥 Final Chat Request Failure: ${error.message}`,
          error.stack
        );
        throw new HttpException(
          `Failed to communicate with ML service after ${maxRetries} attempts: ${error.message}`,
          HttpStatus.SERVICE_UNAVAILABLE
        );
      }
    }
  }

  async makePrediction(
    request: MLPredictionRequest
  ): Promise<MLPredictionResponse> {
    try {
      const response = await this.axiosInstance.post(
        '/api/v1/predict',
        request
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Error making prediction: ${error.message}`,
        error.stack
      );
      throw new HttpException(
        'Failed to make prediction',
        HttpStatus.SERVICE_UNAVAILABLE
      );
    }
  }

  async queryData(request: MLDataQueryRequest): Promise<MLDataQueryResponse> {
    try {
      const response = await this.axiosInstance.post(
        '/api/v1/query-data',
        request
      );
      return response.data;
    } catch (error) {
      this.logger.error(`Error querying data: ${error.message}`, error.stack);
      throw new HttpException(
        'Failed to query data',
        HttpStatus.SERVICE_UNAVAILABLE
      );
    }
  }

  async searchDocuments(
    request: MLDocumentSearchRequest
  ): Promise<MLDocumentSearchResponse> {
    try {
      // ML service expects query parameters for search-docs
      const params = {
        query: request.query,
        use_llm: true,
        max_results: request.limit || 5,
      };

      const response = await this.axiosInstance.post(
        '/api/v1/search-docs',
        null,
        { params }
      );
      return response.data;
    } catch (error) {
      this.logger.error(
        `Error searching documents: ${error.message}`,
        error.stack
      );
      throw new HttpException(
        'Failed to search documents',
        HttpStatus.SERVICE_UNAVAILABLE
      );
    }
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.axiosInstance.get('/api/v1/health');
      return response.status === 200;
    } catch (error) {
      this.logger.error(`ML service health check failed: ${error.message}`);
      return false;
    }
  }

  private handleAxiosError(error: AxiosError): void {
    if (error.response) {
      this.logger.error(
        `ML service responded with error ${
          error.response.status
        }: ${JSON.stringify(error.response.data)}`
      );
    } else if (error.request) {
      this.logger.error(
        'No response received from ML service - possible network issue'
      );
    } else {
      this.logger.error(
        `Error setting up request to ML service: ${error.message}`
      );
    }
  }

  private isRetryableError(error: any): boolean {
    // Retry on network errors, timeouts, and temporary server errors
    if (
      error.code === 'ECONNRESET' ||
      error.code === 'ETIMEDOUT' ||
      error.code === 'ENOTFOUND' ||
      error.code === 'ECONNREFUSED'
    ) {
      return true;
    }

    // Retry on HTTP 5xx errors (server errors) but not 4xx (client errors)
    if (error.response?.status >= 500 && error.response?.status < 600) {
      return true;
    }

    // Retry on timeout errors
    if (error.message?.toLowerCase().includes('timeout')) {
      return true;
    }

    return false;
  }
}
