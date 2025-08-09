import { Injectable, Logger, HttpException, HttpStatus } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  MLRequest,
  MLResponse,
  MLPredictionRequest,
  MLPredictionResponse,
  MLDataQueryRequest,
  MLDataQueryResponse,
  MLDocumentSearchRequest,
  MLDocumentSearchResponse,
} from './interfaces/ml.interface';

@Injectable()
export class MLService {
  private readonly logger = new Logger(MLService.name);
  private readonly axiosInstance: AxiosInstance;
  private readonly mlServiceUrl: string;

  constructor(private readonly configService: ConfigService) {
    this.mlServiceUrl = this.configService.get<string>('ML_SERVICE_URL', 'http://localhost:8000');
    
    this.axiosInstance = axios.create({
      baseURL: this.mlServiceUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.axiosInstance.interceptors.request.use(
      (config) => {
        this.logger.debug(`Making request to ${config.url}`);
        return config;
      },
      (error) => {
        this.logger.error('Request error:', error);
        return Promise.reject(error);
      },
    );

    this.axiosInstance.interceptors.response.use(
      (response) => {
        this.logger.debug(`Response received from ${response.config.url}`);
        return response;
      },
      (error) => {
        this.handleAxiosError(error);
        return Promise.reject(error);
      },
    );
  }

  async sendToMLService(request: MLRequest): Promise<MLResponse> {
    try {
      // ML service expects query parameters, not body data
      const params = {
        message: request.message,
        session_id: request.sessionId,
        user_id: request.context?.userId,
      };
      
      const response = await this.axiosInstance.post('/api/v1/chat', null, { params });
      return response.data;
    } catch (error) {
      this.logger.error(`Error communicating with ML service: ${error.message}`, error.stack);
      throw new HttpException(
        'Failed to communicate with ML service',
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  async makePrediction(request: MLPredictionRequest): Promise<MLPredictionResponse> {
    try {
      const response = await this.axiosInstance.post('/api/v1/predict', request);
      return response.data;
    } catch (error) {
      this.logger.error(`Error making prediction: ${error.message}`, error.stack);
      throw new HttpException(
        'Failed to make prediction',
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  async queryData(request: MLDataQueryRequest): Promise<MLDataQueryResponse> {
    try {
      const response = await this.axiosInstance.post('/api/v1/query-data', request);
      return response.data;
    } catch (error) {
      this.logger.error(`Error querying data: ${error.message}`, error.stack);
      throw new HttpException(
        'Failed to query data',
        HttpStatus.SERVICE_UNAVAILABLE,
      );
    }
  }

  async searchDocuments(request: MLDocumentSearchRequest): Promise<MLDocumentSearchResponse> {
    try {
      // ML service expects query parameters for search-docs
      const params = {
        query: request.query,
        use_llm: true,
        max_results: request.limit || 5,
      };
      
      const response = await this.axiosInstance.post('/api/v1/search-docs', null, { params });
      return response.data;
    } catch (error) {
      this.logger.error(`Error searching documents: ${error.message}`, error.stack);
      throw new HttpException(
        'Failed to search documents',
        HttpStatus.SERVICE_UNAVAILABLE,
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
        `ML service responded with error ${error.response.status}: ${JSON.stringify(error.response.data)}`,
      );
    } else if (error.request) {
      this.logger.error('No response received from ML service');
    } else {
      this.logger.error(`Error setting up request to ML service: ${error.message}`);
    }
  }
}