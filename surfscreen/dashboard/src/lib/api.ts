import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  Job,
  JobListResponse,
  HealthStatus,
  ReadinessStatus,
  JobCreateResponse,
  ScreeningResult,
  MDResult,
  ApiError
} from '@/types';
import { API_URL, API_KEY } from './constants';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      }
    });

    // Request Interceptor - API Key 추가
    this.client.interceptors.request.use((config) => {
      if (API_KEY) {
        config.headers['X-API-Key'] = API_KEY;
      }
      return config;
    });

    // Response Interceptor - 에러 처리
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        const message = error.response?.data?.detail || error.message;
        console.error('API Error:', message);
        throw error;
      }
    );
  }

  // ============ Health ============
  
  async getHealth(): Promise<HealthStatus> {
    const { data } = await this.client.get('/health');
    return data;
  }

  async getReadiness(): Promise<ReadinessStatus> {
    const { data } = await this.client.get('/health/ready');
    return data;
  }

  // ============ Jobs ============
  
  async listJobs(params?: {
    status_filter?: string;
    job_type?: string;
    limit?: number;
  }): Promise<JobListResponse> {
    const { data } = await this.client.get('/api/v1/jobs', { params });
    return data;
  }

  async getJob(jobId: string): Promise<Job> {
    const { data } = await this.client.get(`/api/v1/jobs/${jobId}`);
    return data;
  }

  async cancelJob(jobId: string): Promise<{ message: string; job_id: string }> {
    const { data } = await this.client.delete(`/api/v1/jobs/${jobId}`);
    return data;
  }

  async getJobResult(jobId: string): Promise<Record<string, unknown>> {
    const { data } = await this.client.get(`/api/v1/jobs/${jobId}/result`);
    return data;
  }

  async downloadJobResults(jobId: string): Promise<Blob> {
    const { data } = await this.client.get(`/api/v1/jobs/${jobId}/download`, {
      responseType: 'blob'
    });
    return data;
  }

  async getJobLogs(jobId: string, tail = 100): Promise<{ logs: string; lines: number }> {
    const { data } = await this.client.get(`/api/v1/jobs/${jobId}/logs`, {
      params: { tail }
    });
    return data;
  }

  // ============ Screening ============
  
  async createScreeningJob(formData: FormData): Promise<JobCreateResponse> {
    const { data } = await this.client.post('/api/v1/screening', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    });
    return data;
  }

  async getScreeningResult(jobId: string): Promise<ScreeningResult> {
    const { data } = await this.client.get(`/api/v1/screening/${jobId}/result`);
    return data;
  }

  async getScreeningReport(jobId: string, theme = 'dark'): Promise<string> {
    const { data } = await this.client.get(`/api/v1/screening/${jobId}/report`, {
      params: { theme },
      responseType: 'text'
    });
    return data;
  }

  // ============ MD ============
  
  async createMDJob(formData: FormData): Promise<JobCreateResponse> {
    const { data } = await this.client.post('/api/v1/md', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000
    });
    return data;
  }

  async getMDResult(jobId: string): Promise<MDResult> {
    const { data } = await this.client.get(`/api/v1/md/${jobId}/result`);
    return data;
  }

  async downloadTrajectory(jobId: string, format = 'extxyz'): Promise<Blob> {
    const { data } = await this.client.get(`/api/v1/md/${jobId}/trajectory`, {
      params: { format },
      responseType: 'blob'
    });
    return data;
  }

  async getMDReport(jobId: string, theme = 'dark'): Promise<string> {
    const { data } = await this.client.get(`/api/v1/md/${jobId}/report`, {
      params: { theme },
      responseType: 'text'
    });
    return data;
  }
}

// Singleton instance
export const api = new ApiClient();
export default api;
