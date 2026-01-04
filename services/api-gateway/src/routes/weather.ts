import { Router, Request, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';

const router: RouterType = Router();
const WEATHER_SERVICE_URL = process.env.WEATHER_SERVICE_URL || 'http://localhost:8003';

// Get current weather
router.get('/current', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${WEATHER_SERVICE_URL}/weather/current`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get weather';
    res.status(status).json({ error: message });
  }
});

// Get weather forecast
router.get('/forecast', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${WEATHER_SERVICE_URL}/weather/forecast`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get forecast';
    res.status(status).json({ error: message });
  }
});

// Get weather by location
router.get('/location/:location', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(
      `${WEATHER_SERVICE_URL}/weather/location/${encodeURIComponent(req.params.location)}`,
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get weather for location';
    res.status(status).json({ error: message });
  }
});

export default router;
