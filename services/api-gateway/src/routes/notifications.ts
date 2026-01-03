import { Router, Request, Response } from 'express';
import axios from 'axios';

const router = Router();
const NOTIFICATION_SERVICE_URL = process.env.NOTIFICATION_SERVICE_URL || 'http://localhost:8008';

// List notifications
router.get('/', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${NOTIFICATION_SERVICE_URL}/notifications`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to fetch notifications';
    res.status(status).json({ error: message });
  }
});

// Mark notification as read
router.post('/:notificationId/read', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(
      `${NOTIFICATION_SERVICE_URL}/notifications/${req.params.notificationId}/read`,
      {},
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to mark notification as read';
    res.status(status).json({ error: message });
  }
});

// Mark all notifications as read
router.post('/read-all', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(
      `${NOTIFICATION_SERVICE_URL}/notifications/read-all`,
      {},
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to mark all notifications as read';
    res.status(status).json({ error: message });
  }
});

// Register device for push notifications
router.post('/devices', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(`${NOTIFICATION_SERVICE_URL}/devices`, req.body, {
      headers: {
        'Authorization': req.headers.authorization,
        'Content-Type': 'application/json',
      },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to register device';
    res.status(status).json({ error: message });
  }
});

// List registered devices
router.get('/devices', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${NOTIFICATION_SERVICE_URL}/devices`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to list devices';
    res.status(status).json({ error: message });
  }
});

// Unregister device
router.delete('/devices/:token', async (req: Request, res: Response) => {
  try {
    const response = await axios.delete(
      `${NOTIFICATION_SERVICE_URL}/devices/${req.params.token}`,
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to unregister device';
    res.status(status).json({ error: message });
  }
});

export default router;
