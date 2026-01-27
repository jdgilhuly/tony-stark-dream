import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const memoryRouter: RouterType = Router();

const MEMORY_SERVICE_URL = process.env.MEMORY_SERVICE_URL ?? 'http://localhost:8011';

/**
 * Store a memory
 */
memoryRouter.post('/store', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${MEMORY_SERVICE_URL}/memory/store`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Memory store error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_STORE_ERROR',
        message: error.response?.data?.detail || 'Failed to store memory',
      },
    });
  }
});

/**
 * Search memories
 */
memoryRouter.post('/search', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${MEMORY_SERVICE_URL}/memory/search`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Memory search error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_SEARCH_ERROR',
        message: error.response?.data?.detail || 'Failed to search memories',
      },
    });
  }
});

/**
 * Recall memories (semantic search)
 */
memoryRouter.get('/recall', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { query, limit, types } = req.query;
    const response = await axios.get(
      `${MEMORY_SERVICE_URL}/memory/recall`,
      {
        params: { query, limit, types },
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
    logger.error('Memory recall error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_RECALL_ERROR',
        message: error.response?.data?.detail || 'Failed to recall memories',
      },
    });
  }
});

/**
 * Get memory by ID
 */
memoryRouter.get('/:memoryId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { memoryId } = req.params;
    const response = await axios.get(
      `${MEMORY_SERVICE_URL}/memory/${memoryId}`,
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
    logger.error('Memory get error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_GET_ERROR',
        message: error.response?.data?.detail || 'Failed to get memory',
      },
    });
  }
});

/**
 * Update memory
 */
memoryRouter.put('/:memoryId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { memoryId } = req.params;
    const response = await axios.put(
      `${MEMORY_SERVICE_URL}/memory/${memoryId}`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Memory update error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_UPDATE_ERROR',
        message: error.response?.data?.detail || 'Failed to update memory',
      },
    });
  }
});

/**
 * Delete memory
 */
memoryRouter.delete('/:memoryId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { memoryId } = req.params;
    const response = await axios.delete(
      `${MEMORY_SERVICE_URL}/memory/${memoryId}`,
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
    logger.error('Memory delete error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_DELETE_ERROR',
        message: error.response?.data?.detail || 'Failed to delete memory',
      },
    });
  }
});

/**
 * Get memory statistics
 */
memoryRouter.get('/stats', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.get(
      `${MEMORY_SERVICE_URL}/memory/stats`,
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
    logger.error('Memory stats error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'MEMORY_STATS_ERROR',
        message: error.response?.data?.detail || 'Failed to get memory stats',
      },
    });
  }
});
