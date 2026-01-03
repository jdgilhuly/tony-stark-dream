import { Router, Request, Response } from 'express';
import { v4 as uuidv4 } from 'uuid';
import {
  generateToken,
  generateRefreshToken,
  verifyRefreshToken,
} from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const authRouter = Router();

// In-memory user store for development (replace with database)
const users = new Map<string, { id: string; email: string; password: string; name: string }>();

authRouter.post('/register', async (req: Request, res: Response) => {
  try {
    const { email, password, name } = req.body;

    if (!email || !password || !name) {
      res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Email, password, and name are required' },
      });
      return;
    }

    // Check if user exists
    const existingUser = Array.from(users.values()).find((u) => u.email === email);
    if (existingUser) {
      res.status(409).json({
        success: false,
        error: { code: 'USER_EXISTS', message: 'User already exists' },
      });
      return;
    }

    // Create user (in production, hash the password)
    const userId = uuidv4();
    const user = { id: userId, email, password, name };
    users.set(userId, user);

    const accessToken = generateToken(userId, email);
    const refreshToken = generateRefreshToken(userId);

    logger.info(`User registered: ${email}`);

    res.status(201).json({
      success: true,
      data: {
        user: { id: userId, email, name },
        tokens: {
          accessToken,
          refreshToken,
          expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000),
        },
      },
    });
  } catch (error) {
    logger.error('Registration error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'REGISTRATION_ERROR', message: 'Registration failed' },
    });
  }
});

authRouter.post('/login', async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'Email and password are required' },
      });
      return;
    }

    // Find user
    const user = Array.from(users.values()).find((u) => u.email === email);
    if (!user || user.password !== password) {
      res.status(401).json({
        success: false,
        error: { code: 'INVALID_CREDENTIALS', message: 'Invalid email or password' },
      });
      return;
    }

    const accessToken = generateToken(user.id, email);
    const refreshToken = generateRefreshToken(user.id);

    logger.info(`User logged in: ${email}`);

    res.json({
      success: true,
      data: {
        user: { id: user.id, email: user.email, name: user.name },
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

    const user = users.get(payload.userId);
    if (!user) {
      res.status(401).json({
        success: false,
        error: { code: 'USER_NOT_FOUND', message: 'User not found' },
      });
      return;
    }

    const newAccessToken = generateToken(user.id, user.email);
    const newRefreshToken = generateRefreshToken(user.id);

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
