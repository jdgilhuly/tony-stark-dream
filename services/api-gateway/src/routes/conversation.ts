import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const conversationRouter: RouterType = Router();

// In-memory conversation store (replace with database)
const conversations = new Map<string, {
  id: string;
  userId: string;
  messages: Array<{
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
  }>;
  startedAt: Date;
  lastMessageAt: Date;
}>();

// Conversation service URL (for forwarding requests)
const CONVERSATION_SERVICE_URL = process.env.CONVERSATION_SERVICE_URL ?? 'http://localhost:8001';

conversationRouter.post('/message', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { message, conversationId, contextHints } = req.body;
    const userId = req.user!.userId;

    if (!message) {
      res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Message is required' },
      });
      return;
    }

    // Get or create conversation
    let conversation = conversationId ? conversations.get(conversationId) : null;
    if (!conversation) {
      const newId = uuidv4();
      conversation = {
        id: newId,
        userId,
        messages: [],
        startedAt: new Date(),
        lastMessageAt: new Date(),
      };
      conversations.set(newId, conversation);
    }

    // Add user message
    const userMessage = {
      id: uuidv4(),
      role: 'user' as const,
      content: message,
      timestamp: new Date(),
    };
    conversation.messages.push(userMessage);

    // Forward to conversation service (mock response for now)
    // In production, this would call the Python conversation service
    const assistantResponse = await generateMockResponse(message, conversation.messages);

    const assistantMessage = {
      id: uuidv4(),
      role: 'assistant' as const,
      content: assistantResponse,
      timestamp: new Date(),
    };
    conversation.messages.push(assistantMessage);
    conversation.lastMessageAt = new Date();

    logger.info(`Conversation ${conversation.id}: User sent message`);

    res.json({
      success: true,
      data: {
        id: assistantMessage.id,
        conversationId: conversation.id,
        message: assistantMessage,
        suggestedActions: [],
      },
    });
  } catch (error) {
    logger.error('Conversation error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'CONVERSATION_ERROR', message: 'Failed to process message' },
    });
  }
});

conversationRouter.get('/:conversationId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { conversationId } = req.params;
    const userId = req.user!.userId;

    const conversation = conversations.get(conversationId);
    if (!conversation) {
      res.status(404).json({
        success: false,
        error: { code: 'NOT_FOUND', message: 'Conversation not found' },
      });
      return;
    }

    if (conversation.userId !== userId) {
      res.status(403).json({
        success: false,
        error: { code: 'FORBIDDEN', message: 'Access denied' },
      });
      return;
    }

    res.json({
      success: true,
      data: conversation,
    });
  } catch (error) {
    logger.error('Get conversation error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'FETCH_ERROR', message: 'Failed to fetch conversation' },
    });
  }
});

conversationRouter.get('/:conversationId/history', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { conversationId } = req.params;
    const userId = req.user!.userId;

    const conversation = conversations.get(conversationId);
    if (!conversation || conversation.userId !== userId) {
      res.status(404).json({
        success: false,
        error: { code: 'NOT_FOUND', message: 'Conversation not found' },
      });
      return;
    }

    res.json({
      success: true,
      data: conversation.messages,
    });
  } catch (error) {
    logger.error('Get history error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'FETCH_ERROR', message: 'Failed to fetch history' },
    });
  }
});

conversationRouter.get('/', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const userId = req.user!.userId;
    const userConversations = Array.from(conversations.values())
      .filter((c) => c.userId === userId)
      .sort((a, b) => b.lastMessageAt.getTime() - a.lastMessageAt.getTime());

    res.json({
      success: true,
      data: userConversations.map((c) => ({
        id: c.id,
        startedAt: c.startedAt,
        lastMessageAt: c.lastMessageAt,
        messageCount: c.messages.length,
        preview: c.messages[c.messages.length - 1]?.content.slice(0, 100),
      })),
    });
  } catch (error) {
    logger.error('List conversations error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'FETCH_ERROR', message: 'Failed to fetch conversations' },
    });
  }
});

// Mock response generator (replace with actual conversation service call)
async function generateMockResponse(
  userMessage: string,
  history: Array<{ role: string; content: string }>
): Promise<string> {
  const responses = [
    "Certainly, sir. I shall attend to that right away.",
    "I'm afraid I'll need a moment to process that request, sir.",
    "Might I suggest an alternative approach, sir?",
    "Very well, sir. Consider it done.",
    "I've analyzed the situation, sir. Here's what I recommend...",
    "Sir, I must advise caution with that particular course of action.",
    "Indeed, sir. I'll make the necessary arrangements.",
    "I've taken the liberty of preparing a summary for you, sir.",
  ];

  // Simple mock - in production, this calls the conversation service with Claude
  await new Promise((resolve) => setTimeout(resolve, 500));
  return responses[Math.floor(Math.random() * responses.length)];
}
