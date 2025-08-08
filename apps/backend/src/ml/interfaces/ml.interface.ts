export interface MLRequest {
  message: string;
  sessionId: string;
  context?: Record<string, any>;
  history?: any[];
}

export interface MLPredictionRequest {
  features: {
    age?: number;
    sex?: string;
    bmi?: number;
    medication_count?: number;
    exercise_frequency?: string;
    diet_quality?: string;
    smoker?: string;
    days_hospitalized?: number;
    readmitted?: boolean;
    [key: string]: any;
  };
  target: 'chronic_obstructive_pulmonary_disease' | 'alanine_aminotransferase';
}

export interface MLDataQueryRequest {
  query: string;
  filters?: Record<string, any>;
  aggregations?: string[];
}

export interface MLDocumentSearchRequest {
  query: string;
  limit?: number;
  filters?: Record<string, any>;
}

export interface MLResponse {
  message: string;
  citations?: Array<{
    documentId: string;
    title: string;
    excerpt: string;
    page?: number;
  }>;
  chartData?: {
    type: 'bar' | 'line' | 'pie' | 'scatter';
    data: any;
    options?: any;
  };
  metadata?: Record<string, any>;
}

export interface MLPredictionResponse {
  prediction: string | number;
  confidence?: number;
  feature_importance?: Record<string, number>;
  explanation?: string;
}

export interface MLDataQueryResponse {
  results: any[];
  count: number;
  visualization?: {
    type: string;
    data: any;
  };
}

export interface MLDocumentSearchResponse {
  documents: Array<{
    id: string;
    title: string;
    content: string;
    score: number;
    metadata?: Record<string, any>;
  }>;
  total: number;
}