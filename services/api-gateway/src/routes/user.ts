import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const userRouter: RouterType = Router();

const USER_PROFILE_URL = process.env.USER_PROFILE_URL || 'http://localhost:8009';

/**
 * Proxy request to user-profile service.
 */
async function proxyToUserService(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  path: string,
  token: string,
  data?: unknown
) {
  const url = `${USER_PROFILE_URL}${path}`;
  const response = await axios({
    method,
    url,
    data,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    timeout: 10000,
  });
  return response.data;
}

/**
 * Get current user's profile.
 */
userRouter.get('/profile', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    const profile = await proxyToUserService('get', '/users/me', token);

    res.json({
      success: true,
      data: profile,
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to fetch profile';
      logger.error(`Get profile error: ${status} - ${message}`);
      res.status(status).json({
        success: false,
        error: { code: 'FETCH_ERROR', message },
      });
    } else {
      logger.error('Get profile error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'FETCH_ERROR', message: 'Failed to fetch profile' },
      });
    }
  }
});

/**
 * Update current user's profile.
 */
userRouter.put('/profile', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    const profile = await proxyToUserService('put', '/users/me', token, req.body);

    logger.info(`Profile updated for user ${req.user!.userId}`);

    res.json({
      success: true,
      data: profile,
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to update profile';
      logger.error(`Update profile error: ${status} - ${message}`);
      res.status(status).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message },
      });
    } else {
      logger.error('Update profile error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message: 'Failed to update profile' },
      });
    }
  }
});

/**
 * Get current user's preferences.
 */
userRouter.get('/preferences', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    const preferences = await proxyToUserService('get', '/users/me/preferences', token);

    res.json({
      success: true,
      data: preferences,
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to fetch preferences';
      res.status(status).json({
        success: false,
        error: { code: 'FETCH_ERROR', message },
      });
    } else {
      logger.error('Get preferences error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'FETCH_ERROR', message: 'Failed to fetch preferences' },
      });
    }
  }
});

/**
 * Update current user's preferences.
 */
userRouter.put('/preferences', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    const preferences = await proxyToUserService('patch', '/users/me/preferences', token, req.body);

    logger.info(`Preferences updated for user ${req.user!.userId}`);

    res.json({
      success: true,
      data: preferences,
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to update preferences';
      logger.error(`Update preferences error: ${status} - ${message}`);
      res.status(status).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message },
      });
    } else {
      logger.error('Update preferences error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message: 'Failed to update preferences' },
      });
    }
  }
});

/**
 * Patch preferences (partial update).
 */
userRouter.patch('/preferences', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    const preferences = await proxyToUserService('patch', '/users/me/preferences', token, req.body);

    logger.info(`Preferences patched for user ${req.user!.userId}`);

    res.json({
      success: true,
      data: preferences,
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to update preferences';
      res.status(status).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message },
      });
    } else {
      logger.error('Patch preferences error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'UPDATE_ERROR', message: 'Failed to update preferences' },
      });
    }
  }
});

/**
 * Delete current user's account.
 */
userRouter.delete('/account', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const token = req.headers.authorization?.split(' ')[1] || '';
    await proxyToUserService('delete', '/users/me', token);

    logger.info(`Account deleted for user ${req.user!.userId}`);

    res.json({
      success: true,
      message: 'Account deleted successfully',
    });
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message = error.response?.data?.detail || 'Failed to delete account';
      logger.error(`Delete account error: ${status} - ${message}`);
      res.status(status).json({
        success: false,
        error: { code: 'DELETE_ERROR', message },
      });
    } else {
      logger.error('Delete account error:', error);
      res.status(500).json({
        success: false,
        error: { code: 'DELETE_ERROR', message: 'Failed to delete account' },
      });
    }
  }
});
