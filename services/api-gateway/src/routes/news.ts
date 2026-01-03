import { Router, Request, Response } from 'express';
import axios from 'axios';

const router = Router();
const NEWS_SERVICE_URL = process.env.NEWS_SERVICE_URL || 'http://localhost:8004';

// Get top headlines
router.get('/headlines', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${NEWS_SERVICE_URL}/news/headlines`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get headlines';
    res.status(status).json({ error: message });
  }
});

// Search news
router.get('/search', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${NEWS_SERVICE_URL}/news/search`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to search news';
    res.status(status).json({ error: message });
  }
});

// Get news by category
router.get('/category/:category', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(
      `${NEWS_SERVICE_URL}/news/category/${req.params.category}`,
      {
        headers: { 'Authorization': req.headers.authorization },
        params: req.query,
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get news by category';
    res.status(status).json({ error: message });
  }
});

// Get personalized news
router.get('/personalized', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${NEWS_SERVICE_URL}/news/personalized`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get personalized news';
    res.status(status).json({ error: message });
  }
});

export default router;
