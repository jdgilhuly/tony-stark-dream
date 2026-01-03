/**
 * Test setup file for API Gateway tests.
 */

import { vi } from 'vitest';

// Mock environment variables
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-secret';
process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/test';
process.env.REDIS_URL = 'redis://localhost:6379/0';

// Mock external service URLs
process.env.CONVERSATION_SERVICE_URL = 'http://localhost:8001';
process.env.VOICE_PROCESSING_URL = 'http://localhost:8002';
process.env.WEATHER_SERVICE_URL = 'http://localhost:8003';
process.env.NEWS_SERVICE_URL = 'http://localhost:8004';
process.env.BRIEFING_SERVICE_URL = 'http://localhost:8005';
process.env.CALENDAR_SERVICE_URL = 'http://localhost:8006';
process.env.TASK_EXECUTION_URL = 'http://localhost:8007';
process.env.NOTIFICATION_SERVICE_URL = 'http://localhost:8008';
process.env.USER_PROFILE_URL = 'http://localhost:8009';

// Global test utilities
vi.mock('../utils/logger.js', () => ({
  logger: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
  },
}));
