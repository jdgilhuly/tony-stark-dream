import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const browserRouter: RouterType = Router();

const BROWSER_SERVICE_URL = process.env.BROWSER_SERVICE_URL ?? 'http://localhost:8012';

/**
 * Create browser session
 */
browserRouter.post('/session', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/session`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 60000, // Browser startup can be slow
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Browser session create error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_SESSION_ERROR',
        message: error.response?.data?.detail || 'Failed to create browser session',
      },
    });
  }
});

/**
 * Close browser session
 */
browserRouter.delete('/session/:sessionId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { sessionId } = req.params;
    const response = await axios.delete(
      `${BROWSER_SERVICE_URL}/browser/session/${sessionId}`,
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
    logger.error('Browser session close error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_SESSION_CLOSE_ERROR',
        message: error.response?.data?.detail || 'Failed to close browser session',
      },
    });
  }
});

/**
 * Navigate to URL
 */
browserRouter.post('/navigate', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/navigate`,
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
    logger.error('Browser navigate error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_NAVIGATE_ERROR',
        message: error.response?.data?.detail || 'Failed to navigate',
      },
    });
  }
});

/**
 * Take screenshot
 */
browserRouter.post('/screenshot', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/screenshot`,
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
    logger.error('Browser screenshot error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_SCREENSHOT_ERROR',
        message: error.response?.data?.detail || 'Failed to take screenshot',
      },
    });
  }
});

/**
 * Scrape page content
 */
browserRouter.post('/scrape', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/scrape`,
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
    logger.error('Browser scrape error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_SCRAPE_ERROR',
        message: error.response?.data?.detail || 'Failed to scrape page',
      },
    });
  }
});

/**
 * Click element
 */
browserRouter.post('/click', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/click`,
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
    logger.error('Browser click error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_CLICK_ERROR',
        message: error.response?.data?.detail || 'Failed to click element',
      },
    });
  }
});

/**
 * Type text
 */
browserRouter.post('/type', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/type`,
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
    logger.error('Browser type error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_TYPE_ERROR',
        message: error.response?.data?.detail || 'Failed to type text',
      },
    });
  }
});

/**
 * Fill form
 */
browserRouter.post('/fill-form', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/fill-form`,
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
    logger.error('Browser fill form error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_FORM_ERROR',
        message: error.response?.data?.detail || 'Failed to fill form',
      },
    });
  }
});

/**
 * Execute JavaScript
 */
browserRouter.post('/execute', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/execute`,
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
    logger.error('Browser execute error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_EXECUTE_ERROR',
        message: error.response?.data?.detail || 'Failed to execute script',
      },
    });
  }
});

/**
 * Get PDF of page
 */
browserRouter.post('/pdf', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${BROWSER_SERVICE_URL}/browser/pdf`,
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
    logger.error('Browser PDF error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'BROWSER_PDF_ERROR',
        message: error.response?.data?.detail || 'Failed to generate PDF',
      },
    });
  }
});
