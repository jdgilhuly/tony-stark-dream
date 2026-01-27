import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const researchRouter: RouterType = Router();

const RESEARCH_SERVICE_URL = process.env.RESEARCH_SERVICE_URL ?? 'http://localhost:8014';

/**
 * Conduct research on a topic
 */
researchRouter.post('/research', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/research`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 300000, // 5 min for research
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Research error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'RESEARCH_ERROR',
        message: error.response?.data?.detail || 'Failed to conduct research',
      },
    });
  }
});

/**
 * Web search
 */
researchRouter.post('/search', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/search`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 60000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Search error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'SEARCH_ERROR',
        message: error.response?.data?.detail || 'Failed to search',
      },
    });
  }
});

/**
 * Extract content from URL
 */
researchRouter.post('/extract', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/extract`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 60000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Extract error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'EXTRACT_ERROR',
        message: error.response?.data?.detail || 'Failed to extract content',
      },
    });
  }
});

/**
 * Synthesize research findings
 */
researchRouter.post('/synthesize', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/synthesize`,
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
    logger.error('Synthesize error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'SYNTHESIZE_ERROR',
        message: error.response?.data?.detail || 'Failed to synthesize research',
      },
    });
  }
});

/**
 * Knowledge base operations
 */
researchRouter.post('/knowledge/store', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/knowledge/store`,
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
    logger.error('Knowledge store error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'KNOWLEDGE_STORE_ERROR',
        message: error.response?.data?.detail || 'Failed to store knowledge',
      },
    });
  }
});

researchRouter.post('/knowledge/search', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${RESEARCH_SERVICE_URL}/knowledge/search`,
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
    logger.error('Knowledge search error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'KNOWLEDGE_SEARCH_ERROR',
        message: error.response?.data?.detail || 'Failed to search knowledge',
      },
    });
  }
});

/**
 * Get research history
 */
researchRouter.get('/history', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.get(
      `${RESEARCH_SERVICE_URL}/history`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Research history error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'RESEARCH_HISTORY_ERROR',
        message: error.response?.data?.detail || 'Failed to get research history',
      },
    });
  }
});

/**
 * Get a specific research result
 */
researchRouter.get('/:researchId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { researchId } = req.params;
    const response = await axios.get(
      `${RESEARCH_SERVICE_URL}/research/${researchId}`,
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
    logger.error('Get research error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GET_RESEARCH_ERROR',
        message: error.response?.data?.detail || 'Failed to get research',
      },
    });
  }
});
