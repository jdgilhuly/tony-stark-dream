import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const claudeRouter: RouterType = Router();

const CLAUDE_SERVICE_URL = process.env.CLAUDE_SERVICE_URL ?? 'http://localhost:8013';

/**
 * Send message to Claude (simple)
 */
claudeRouter.post('/ask', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${CLAUDE_SERVICE_URL}/claude/ask`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 120000, // 2 min for AI response
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude ask error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_ASK_ERROR',
        message: error.response?.data?.detail || 'Failed to get Claude response',
      },
    });
  }
});

/**
 * Chat with Claude (multi-turn with history)
 */
claudeRouter.post('/chat', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${CLAUDE_SERVICE_URL}/claude/chat`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 120000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude chat error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_CHAT_ERROR',
        message: error.response?.data?.detail || 'Failed to chat with Claude',
      },
    });
  }
});

/**
 * Claude with tool use
 */
claudeRouter.post('/tool-use', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${CLAUDE_SERVICE_URL}/claude/tool-use`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 300000, // 5 min for tool use
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude tool use error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_TOOL_ERROR',
        message: error.response?.data?.detail || 'Failed to use Claude tools',
      },
    });
  }
});

/**
 * Stream response from Claude
 */
claudeRouter.post('/stream', async (req: AuthenticatedRequest, res: Response) => {
  try {
    // Set up SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const response = await axios.post(
      `${CLAUDE_SERVICE_URL}/claude/stream`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        responseType: 'stream',
        timeout: 300000,
      }
    );

    // Pipe the stream
    response.data.pipe(res);

    // Handle stream errors
    response.data.on('error', (error: Error) => {
      logger.error('Claude stream error:', error);
      res.end();
    });

  } catch (error: any) {
    logger.error('Claude stream setup error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_STREAM_ERROR',
        message: error.response?.data?.detail || 'Failed to stream from Claude',
      },
    });
  }
});

/**
 * Code execution with Claude
 */
claudeRouter.post('/code', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${CLAUDE_SERVICE_URL}/claude/code`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 600000, // 10 min for code tasks
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude code error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_CODE_ERROR',
        message: error.response?.data?.detail || 'Failed to execute code task',
      },
    });
  }
});

/**
 * List available tools
 */
claudeRouter.get('/tools', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.get(
      `${CLAUDE_SERVICE_URL}/claude/tools`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude tools list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_TOOLS_ERROR',
        message: error.response?.data?.detail || 'Failed to list tools',
      },
    });
  }
});

/**
 * Get Claude usage/stats
 */
claudeRouter.get('/usage', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.get(
      `${CLAUDE_SERVICE_URL}/claude/usage`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Claude usage error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CLAUDE_USAGE_ERROR',
        message: error.response?.data?.detail || 'Failed to get usage stats',
      },
    });
  }
});
