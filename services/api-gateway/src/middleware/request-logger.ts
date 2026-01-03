import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';
import { logger } from '../utils/logger.js';

export interface RequestWithId extends Request {
  requestId?: string;
  startTime?: number;
}

export const requestLogger = (
  req: RequestWithId,
  res: Response,
  next: NextFunction
): void => {
  req.requestId = uuidv4();
  req.startTime = Date.now();

  res.setHeader('X-Request-ID', req.requestId);

  logger.info(`${req.method} ${req.path}`, {
    requestId: req.requestId,
    ip: req.ip,
    userAgent: req.get('user-agent'),
  });

  res.on('finish', () => {
    const duration = Date.now() - (req.startTime ?? Date.now());
    logger.info(`${req.method} ${req.path} ${res.statusCode}`, {
      requestId: req.requestId,
      duration: `${duration}ms`,
      statusCode: res.statusCode,
    });
  });

  next();
};
