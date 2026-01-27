import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const orchestrationRouter: RouterType = Router();

const ORCHESTRATION_SERVICE_URL = process.env.ORCHESTRATION_SERVICE_URL ?? 'http://localhost:8016';

/**
 * Execute a single task
 */
orchestrationRouter.post('/task', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/task`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 600000, // 10 min for tasks
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Task execution error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'TASK_EXECUTION_ERROR',
        message: error.response?.data?.detail || 'Failed to execute task',
      },
    });
  }
});

/**
 * Create and execute workflow
 */
orchestrationRouter.post('/workflow', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/workflow`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 1800000, // 30 min for workflows
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Workflow execution error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'WORKFLOW_EXECUTION_ERROR',
        message: error.response?.data?.detail || 'Failed to execute workflow',
      },
    });
  }
});

/**
 * Get workflow status
 */
orchestrationRouter.get('/workflow/:workflowId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { workflowId } = req.params;
    const response = await axios.get(
      `${ORCHESTRATION_SERVICE_URL}/workflow/${workflowId}`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Workflow get error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'WORKFLOW_GET_ERROR',
        message: error.response?.data?.detail || 'Failed to get workflow',
      },
    });
  }
});

/**
 * Cancel workflow
 */
orchestrationRouter.delete('/workflow/:workflowId', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { workflowId } = req.params;
    const response = await axios.delete(
      `${ORCHESTRATION_SERVICE_URL}/workflow/${workflowId}`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Workflow cancel error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'WORKFLOW_CANCEL_ERROR',
        message: error.response?.data?.detail || 'Failed to cancel workflow',
      },
    });
  }
});

/**
 * Execute code task (high-level template)
 */
orchestrationRouter.post('/code-task', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/code-task`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 600000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Code task error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'CODE_TASK_ERROR',
        message: error.response?.data?.detail || 'Failed to execute code task',
      },
    });
  }
});

/**
 * Execute research task (high-level template)
 */
orchestrationRouter.post('/research-task', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/research-task`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 600000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Research task error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'RESEARCH_TASK_ERROR',
        message: error.response?.data?.detail || 'Failed to execute research task',
      },
    });
  }
});

/**
 * Execute automation task (high-level template)
 */
orchestrationRouter.post('/automation-task', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/automation-task`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 600000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Automation task error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'AUTOMATION_TASK_ERROR',
        message: error.response?.data?.detail || 'Failed to execute automation task',
      },
    });
  }
});

/**
 * Natural language task execution
 * The main "do anything" endpoint
 */
orchestrationRouter.post('/do', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { task } = req.body;

    if (!task) {
      res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Task description is required',
        },
      });
      return;
    }

    const response = await axios.post(
      `${ORCHESTRATION_SERVICE_URL}/do`,
      null,
      {
        params: { task },
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        timeout: 600000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('Do task error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'DO_TASK_ERROR',
        message: error.response?.data?.detail || 'Failed to execute task',
      },
    });
  }
});
