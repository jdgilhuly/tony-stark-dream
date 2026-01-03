import { Router, Request, Response } from 'express';
import axios from 'axios';

const router = Router();
const TASK_EXECUTION_URL = process.env.TASK_EXECUTION_URL || 'http://localhost:8007';

// Proxy all task requests to the task execution service
router.post('/', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(`${TASK_EXECUTION_URL}/tasks`, req.body, {
      headers: {
        'Authorization': req.headers.authorization,
        'Content-Type': 'application/json',
      },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Task creation failed';
    res.status(status).json({ error: message });
  }
});

router.get('/', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${TASK_EXECUTION_URL}/tasks`, {
      headers: { 'Authorization': req.headers.authorization },
      params: req.query,
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to fetch tasks';
    res.status(status).json({ error: message });
  }
});

router.get('/:taskId', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${TASK_EXECUTION_URL}/tasks/${req.params.taskId}`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Task not found';
    res.status(status).json({ error: message });
  }
});

router.patch('/:taskId', async (req: Request, res: Response) => {
  try {
    const response = await axios.patch(
      `${TASK_EXECUTION_URL}/tasks/${req.params.taskId}`,
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
    const message = error.response?.data?.detail || 'Task update failed';
    res.status(status).json({ error: message });
  }
});

router.delete('/:taskId', async (req: Request, res: Response) => {
  try {
    const response = await axios.delete(`${TASK_EXECUTION_URL}/tasks/${req.params.taskId}`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Task deletion failed';
    res.status(status).json({ error: message });
  }
});

router.post('/:taskId/execute', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(
      `${TASK_EXECUTION_URL}/tasks/${req.params.taskId}/execute`,
      {},
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Task execution failed';
    res.status(status).json({ error: message });
  }
});

router.post('/:taskId/cancel', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(
      `${TASK_EXECUTION_URL}/tasks/${req.params.taskId}/cancel`,
      {},
      {
        headers: { 'Authorization': req.headers.authorization },
      }
    );
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Task cancellation failed';
    res.status(status).json({ error: message });
  }
});

export default router;
