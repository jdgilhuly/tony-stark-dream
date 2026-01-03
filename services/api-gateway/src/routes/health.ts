import { Router } from 'express';

export const healthRouter = Router();

healthRouter.get('/', (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'healthy',
      service: 'api-gateway',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    },
  });
});

healthRouter.get('/ready', (req, res) => {
  // Add service dependency checks here
  const isReady = true;

  if (isReady) {
    res.json({
      success: true,
      data: { status: 'ready' },
    });
  } else {
    res.status(503).json({
      success: false,
      error: { code: 'NOT_READY', message: 'Service not ready' },
    });
  }
});

healthRouter.get('/live', (req, res) => {
  res.json({
    success: true,
    data: { status: 'alive' },
  });
});
