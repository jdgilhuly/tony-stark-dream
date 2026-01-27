import { Router, Request, Response } from 'express';
import type { Router as RouterType } from 'express';
import {
  generateToken,
  generateRefreshToken,
  verifyRefreshToken,
} from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const authRouter: RouterType = Router();

// Check if auth is disabled
const isAuthDisabled = () => process.env.AUTH_DISABLED === 'true';

// Get master password from env
const getMasterPassword = () => process.env.JARVIS_PASSWORD;

// Default user for simplified auth
const DEFAULT_USER_ID = 'jarvis-user';
const DEFAULT_EMAIL = 'jarvis@local';
const DEFAULT_NAME = 'JARVIS User';

// Registration is a no-op in simplified auth - kept for API compatibility
authRouter.post('/register', async (req: Request, res: Response) => {
  // If auth is disabled, just return success
  if (isAuthDisabled()) {
    const accessToken = generateToken(DEFAULT_USER_ID, DEFAULT_EMAIL);
    const refreshToken = generateRefreshToken(DEFAULT_USER_ID);

    res.status(201).json({
      success: true,
      data: {
        user: { id: DEFAULT_USER_ID, email: DEFAULT_EMAIL, name: DEFAULT_NAME },
        tokens: {
          accessToken,
          refreshToken,
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      },
    });
    return;
  }

  // Registration not supported in simplified auth mode - direct to login
  res.status(400).json({
    success: false,
    error: { code: 'NOT_SUPPORTED', message: 'Registration not supported. Use login with JARVIS_PASSWORD.' },
  });
});

authRouter.post('/login', async (req: Request, res: Response) => {
  try {
    // If auth is disabled, return tokens without checking password
    if (isAuthDisabled()) {
      const accessToken = generateToken(DEFAULT_USER_ID, DEFAULT_EMAIL);
      const refreshToken = generateRefreshToken(DEFAULT_USER_ID);

      logger.info('Auth disabled - auto-login');

      res.json({
        success: true,
        data: {
          user: { id: DEFAULT_USER_ID, email: DEFAULT_EMAIL, name: DEFAULT_NAME },
          tokens: {
            accessToken,
            refreshToken,
            expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
          },
        },
      });
      return;
    }

    const { password } = req.body;

    if (!password) {
      res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Password is required' },
      });
      return;
    }

    const masterPassword = getMasterPassword();

    if (!masterPassword) {
      logger.error('JARVIS_PASSWORD not set');
      res.status(500).json({
        success: false,
        error: { code: 'CONFIG_ERROR', message: 'Server not configured. Set JARVIS_PASSWORD environment variable.' },
      });
      return;
    }

    // Check password against master password
    if (password !== masterPassword) {
      res.status(401).json({
        success: false,
        error: { code: 'INVALID_CREDENTIALS', message: 'Invalid password' },
      });
      return;
    }

    const accessToken = generateToken(DEFAULT_USER_ID, DEFAULT_EMAIL);
    const refreshToken = generateRefreshToken(DEFAULT_USER_ID);

    logger.info('User logged in with master password');

    res.json({
      success: true,
      data: {
        user: { id: DEFAULT_USER_ID, email: DEFAULT_EMAIL, name: DEFAULT_NAME },
        tokens: {
          accessToken,
          refreshToken,
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      },
    });
  } catch (error) {
    logger.error('Login error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'LOGIN_ERROR', message: 'Login failed' },
    });
  }
});

authRouter.post('/refresh', async (req: Request, res: Response) => {
  try {
    // If auth is disabled, just return new tokens
    if (isAuthDisabled()) {
      const newAccessToken = generateToken(DEFAULT_USER_ID, DEFAULT_EMAIL);
      const newRefreshToken = generateRefreshToken(DEFAULT_USER_ID);

      res.json({
        success: true,
        data: {
          accessToken: newAccessToken,
          refreshToken: newRefreshToken,
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      });
      return;
    }

    const { refreshToken } = req.body;

    if (!refreshToken) {
      res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Refresh token is required' },
      });
      return;
    }

    const payload = verifyRefreshToken(refreshToken);
    if (!payload) {
      res.status(401).json({
        success: false,
        error: { code: 'INVALID_REFRESH_TOKEN', message: 'Invalid refresh token' },
      });
      return;
    }

    // In simplified auth, we just issue new tokens for the default user
    const newAccessToken = generateToken(DEFAULT_USER_ID, DEFAULT_EMAIL);
    const newRefreshToken = generateRefreshToken(DEFAULT_USER_ID);

    res.json({
      success: true,
      data: {
        accessToken: newAccessToken,
        refreshToken: newRefreshToken,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
      },
    });
  } catch (error) {
    logger.error('Refresh token error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'REFRESH_ERROR', message: 'Token refresh failed' },
    });
  }
});

authRouter.post('/logout', (req: Request, res: Response) => {
  // In production, invalidate the refresh token in the database
  res.json({
    success: true,
    data: { message: 'Logged out successfully' },
  });
});
