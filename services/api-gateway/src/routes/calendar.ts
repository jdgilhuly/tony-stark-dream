import { Router, Request, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';

const router: RouterType = Router();
const CALENDAR_SERVICE_URL = process.env.CALENDAR_SERVICE_URL || 'http://localhost:8006';

// Get OAuth authorization URL
router.get('/auth/url', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${CALENDAR_SERVICE_URL}/auth/url`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get auth URL';
    res.status(status).json({ error: message });
  }
});

// Handle OAuth callback
router.get('/auth/callback', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${CALENDAR_SERVICE_URL}/auth/callback`, {
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'OAuth callback failed';
    res.status(status).json({ error: message });
  }
});

// Get calendar integration status
router.get('/status', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${CALENDAR_SERVICE_URL}/status`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get status';
    res.status(status).json({ error: message });
  }
});

// Get calendar events
router.get('/events', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${CALENDAR_SERVICE_URL}/events`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get events';
    res.status(status).json({ error: message });
  }
});

// Create calendar event
router.post('/events', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(`${CALENDAR_SERVICE_URL}/events`, req.body, {
      headers: {
        'Authorization': req.headers.authorization,
        'Content-Type': 'application/json',
      },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to create event';
    res.status(status).json({ error: message });
  }
});

// Update calendar event
router.patch('/events/:eventId', async (req: Request, res: Response) => {
  try {
    const response = await axios.patch(
      `${CALENDAR_SERVICE_URL}/events/${req.params.eventId}`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization,
          'Content-Type': 'application/json',
        },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to update event';
    res.status(status).json({ error: message });
  }
});

// Delete calendar event
router.delete('/events/:eventId', async (req: Request, res: Response) => {
  try {
    const response = await axios.delete(
      `${CALENDAR_SERVICE_URL}/events/${req.params.eventId}`,
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to delete event';
    res.status(status).json({ error: message });
  }
});

// Disconnect calendar
router.post('/disconnect', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(
      `${CALENDAR_SERVICE_URL}/disconnect`,
      {},
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to disconnect';
    res.status(status).json({ error: message });
  }
});

export default router;
