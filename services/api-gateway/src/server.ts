import express, { Application } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { authRouter } from './routes/auth.js';
import { conversationRouter } from './routes/conversation.js';
import { userRouter } from './routes/user.js';
import { briefingRouter } from './routes/briefing.js';
import { healthRouter } from './routes/health.js';
import tasksRouter from './routes/tasks.js';
import notificationsRouter from './routes/notifications.js';
import voiceRouter from './routes/voice.js';
import calendarRouter from './routes/calendar.js';
import weatherRouter from './routes/weather.js';
import newsRouter from './routes/news.js';
import { errorHandler } from './middleware/error-handler.js';
import { requestLogger } from './middleware/request-logger.js';
import { authenticate, optionalAuth } from './middleware/auth.js';
import { handleWebSocketConnection } from './websocket/handler.js';
import { logger } from './utils/logger.js';

const app: Application = express();
const server = createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

// Configuration
const PORT = process.env.PORT ?? 3000;
const CORS_ORIGIN = process.env.CORS_ORIGIN ?? '*';

// Security middleware
app.use(helmet());
app.use(cors({ origin: CORS_ORIGIN, credentials: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: { error: { code: 'RATE_LIMIT_EXCEEDED', message: 'Too many requests' } },
});
app.use(limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use(requestLogger);

// Health check (no auth)
app.use('/health', healthRouter);

// Auth routes (public)
app.use('/auth', authRouter);

// Protected routes
app.use('/conversation', authenticate, conversationRouter);
app.use('/user', authenticate, userRouter);
app.use('/briefing', authenticate, briefingRouter);
app.use('/tasks', authenticate, tasksRouter);
app.use('/notifications', authenticate, notificationsRouter);
app.use('/voice', authenticate, voiceRouter);
app.use('/calendar', authenticate, calendarRouter);
app.use('/weather', authenticate, weatherRouter);
app.use('/news', authenticate, newsRouter);

// Error handling
app.use(errorHandler);

// WebSocket handling
wss.on('connection', (ws, req) => {
  handleWebSocketConnection(ws, req);
});

// Graceful shutdown
const shutdown = () => {
  logger.info('Shutting down gracefully...');

  wss.clients.forEach((client) => {
    client.close(1001, 'Server shutting down');
  });

  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });

  setTimeout(() => {
    logger.error('Forced shutdown');
    process.exit(1);
  }, 10000);
};

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

// Start server
server.listen(PORT, () => {
  logger.info(`API Gateway listening on port ${PORT}`);
  logger.info(`WebSocket server ready at ws://localhost:${PORT}/ws`);
});

export { app, server, wss };
