import axios from 'axios';
import type { ApiResponse } from '@/types/api';

const javaClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

javaClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('jwt-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

javaClient.interceptors.response.use(
  (res) => {
    const body = res.data as ApiResponse<unknown>;
    // auth endpoints return 200 with code field in body
    if (body && typeof body === 'object' && 'code' in body && body.code !== 200) {
      if (body.code === 401) {
        localStorage.removeItem('jwt-token');
        localStorage.removeItem('jwt-username');
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
      return Promise.reject(new Error(body.msg || 'request failed'));
    }
    return res;
  },
  (err) => {
    if (err.response?.status === 401 || err.response?.status === 403) {
      localStorage.removeItem('jwt-token');
      localStorage.removeItem('jwt-username');
      window.dispatchEvent(new CustomEvent('auth:expired'));
    }
    return Promise.reject(err);
  }
);

export { javaClient };
