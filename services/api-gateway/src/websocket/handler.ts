import { WebSocket } from 'ws';
import { IncomingMessage } from 'http';
import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger.js';
import type { JwtPayload } from '../middleware/auth.js';

const JWT_SECRET = process.env.JWT_SECRET ?? 'development-secret-change-in-production';

interface WebSocketClient extends WebSocket {
  id: string;
  userId?: string;
  isAlive: boolean;
}

interface WebSocketMessage {
  type: string;
  payload: unknown;
  correlationId?: string;
}

const clients = new Map<string, WebSocketClient>();
const userSockets = new Map<string, Set<string>>();

export const handleWebSocketConnection = (ws: WebSocket, req: IncomingMessage): void => {
  const client = ws as WebSocketClient;
  client.id = uuidv4();
  client.isAlive = true;

  // Parse token from query string
  const url = new URL(req.url ?? '', `http://${req.headers.host}`);
  const token = url.searchParams.get('token');

  if (token) {
    try {
      const decoded = jwt.verify(token, JWT_SECRET) as JwtPayload;
      client.userId = decoded.userId;

      // Track user's sockets
      if (!userSockets.has(decoded.userId)) {
        userSockets.set(decoded.userId, new Set());
      }
      userSockets.get(decoded.userId)!.add(client.id);

      logger.info(`WebSocket connected: ${client.id} (user: ${decoded.userId})`);
    } catch {
      logger.warn(`WebSocket invalid token: ${client.id}`);
    }
  } else {
    logger.info(`WebSocket connected (unauthenticated): ${client.id}`);
  }

  clients.set(client.id, client);

  // Send connection acknowledgment
  sendMessage(client, {
    type: 'connection',
    payload: { clientId: client.id, authenticated: !!client.userId },
  });

  // Handle pong for heartbeat
  client.on('pong', () => {
    client.isAlive = true;
  });

  // Handle incoming messages
  client.on('message', (data) => {
    try {
      const message = JSON.parse(data.toString()) as WebSocketMessage;
      handleMessage(client, message);
    } catch (error) {
      logger.error('WebSocket message parse error:', error);
      sendMessage(client, {
        type: 'error',
        payload: { code: 'PARSE_ERROR', message: 'Invalid message format' },
      });
    }
  });

  // Handle close
  client.on('close', () => {
    clients.delete(client.id);
    if (client.userId) {
      const userSocketSet = userSockets.get(client.userId);
      if (userSocketSet) {
        userSocketSet.delete(client.id);
        if (userSocketSet.size === 0) {
          userSockets.delete(client.userId);
        }
      }
    }
    logger.info(`WebSocket disconnected: ${client.id}`);
  });

  // Handle errors
  client.on('error', (error) => {
    logger.error(`WebSocket error (${client.id}):`, error);
  });
};

const handleMessage = (client: WebSocketClient, message: WebSocketMessage): void => {
  const { type, payload, correlationId } = message;

  switch (type) {
    case 'ping':
      sendMessage(client, { type: 'pong', payload: {}, correlationId });
      break;

    case 'conversation:message':
      handleConversationMessage(client, payload, correlationId);
      break;

    case 'voice:start':
      handleVoiceStart(client, correlationId);
      break;

    case 'voice:audio':
      handleVoiceAudio(client, payload, correlationId);
      break;

    case 'voice:stop':
      handleVoiceStop(client, correlationId);
      break;

    default:
      sendMessage(client, {
        type: 'error',
        payload: { code: 'UNKNOWN_TYPE', message: `Unknown message type: ${type}` },
        correlationId,
      });
  }
};

const handleConversationMessage = async (
  client: WebSocketClient,
  payload: unknown,
  correlationId?: string
): Promise<void> => {
  if (!client.userId) {
    sendMessage(client, {
      type: 'error',
      payload: { code: 'UNAUTHORIZED', message: 'Authentication required' },
      correlationId,
    });
    return;
  }

  const { message, conversationId } = payload as { message: string; conversationId?: string };

  // Mock response (in production, forward to conversation service)
  const responses = [
    "Certainly, sir. I shall attend to that right away.",
    "I'm afraid I'll need a moment to process that request, sir.",
    "Very well, sir. Consider it done.",
  ];

  // Simulate processing delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  sendMessage(client, {
    type: 'conversation:response',
    payload: {
      conversationId: conversationId ?? uuidv4(),
      message: {
        id: uuidv4(),
        role: 'assistant',
        content: responses[Math.floor(Math.random() * responses.length)],
        timestamp: new Date(),
      },
    },
    correlationId,
  });
};

const handleVoiceStart = (client: WebSocketClient, correlationId?: string): void => {
  if (!client.userId) {
    sendMessage(client, {
      type: 'error',
      payload: { code: 'UNAUTHORIZED', message: 'Authentication required' },
      correlationId,
    });
    return;
  }

  sendMessage(client, {
    type: 'voice:ready',
    payload: { sessionId: uuidv4() },
    correlationId,
  });
};

const handleVoiceAudio = (
  client: WebSocketClient,
  payload: unknown,
  correlationId?: string
): void => {
  // In production, stream to AWS Transcribe
  sendMessage(client, {
    type: 'voice:partial',
    payload: { text: 'Processing...', isFinal: false },
    correlationId,
  });
};

const handleVoiceStop = (client: WebSocketClient, correlationId?: string): void => {
  // In production, finalize transcription and get response
  sendMessage(client, {
    type: 'voice:final',
    payload: { text: 'Transcription complete.', isFinal: true },
    correlationId,
  });
};

const sendMessage = (client: WebSocketClient, message: Omit<WebSocketMessage, 'timestamp'> & { timestamp?: Date }): void => {
  if (client.readyState === WebSocket.OPEN) {
    client.send(JSON.stringify({ ...message, timestamp: new Date() }));
  }
};

export const sendToUser = (userId: string, message: Omit<WebSocketMessage, 'timestamp'>): void => {
  const socketIds = userSockets.get(userId);
  if (socketIds) {
    socketIds.forEach((socketId) => {
      const client = clients.get(socketId);
      if (client) {
        sendMessage(client, message);
      }
    });
  }
};

export const broadcast = (message: Omit<WebSocketMessage, 'timestamp'>): void => {
  clients.forEach((client) => {
    sendMessage(client, message);
  });
};

// Heartbeat interval to detect dead connections
setInterval(() => {
  clients.forEach((client) => {
    if (!client.isAlive) {
      client.terminate();
      clients.delete(client.id);
      return;
    }
    client.isAlive = false;
    client.ping();
  });
}, 30000);
