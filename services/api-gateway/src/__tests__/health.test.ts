import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import request from 'supertest';
import express from 'express';
import { healthRouter } from '../routes/health.js';

describe('Health Router', () => {
  let app: express.Application;

  beforeAll(() => {
    app = express();
    app.use('/health', healthRouter);
  });

  describe('GET /health', () => {
    it('should return 200 OK', async () => {
      const response = await request(app).get('/health');
      expect(response.status).toBe(200);
    });

    it('should return healthy status', async () => {
      const response = await request(app).get('/health');
      expect(response.body).toHaveProperty('status', 'healthy');
    });

    it('should return service name', async () => {
      const response = await request(app).get('/health');
      expect(response.body).toHaveProperty('service', 'api-gateway');
    });

    it('should return timestamp', async () => {
      const response = await request(app).get('/health');
      expect(response.body).toHaveProperty('timestamp');
    });

    it('should return uptime', async () => {
      const response = await request(app).get('/health');
      expect(response.body).toHaveProperty('uptime');
      expect(typeof response.body.uptime).toBe('number');
    });
  });

  describe('GET /health/ready', () => {
    it('should return 200 when ready', async () => {
      const response = await request(app).get('/health/ready');
      expect(response.status).toBe(200);
    });

    it('should return ready status', async () => {
      const response = await request(app).get('/health/ready');
      expect(response.body).toHaveProperty('ready', true);
    });
  });

  describe('GET /health/live', () => {
    it('should return 200 when alive', async () => {
      const response = await request(app).get('/health/live');
      expect(response.status).toBe(200);
    });

    it('should return alive status', async () => {
      const response = await request(app).get('/health/live');
      expect(response.body).toHaveProperty('alive', true);
    });
  });
});
