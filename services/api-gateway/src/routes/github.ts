import { Router, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const githubRouter: RouterType = Router();

const GITHUB_SERVICE_URL = process.env.GITHUB_SERVICE_URL ?? 'http://localhost:8015';

/**
 * List repositories
 */
githubRouter.get('/repos', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub repos list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_REPOS_ERROR',
        message: error.response?.data?.detail || 'Failed to list repositories',
      },
    });
  }
});

/**
 * Get repository details
 */
githubRouter.get('/repos/:owner/:repo', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}`,
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
    logger.error('GitHub repo get error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_REPO_ERROR',
        message: error.response?.data?.detail || 'Failed to get repository',
      },
    });
  }
});

/**
 * List issues
 */
githubRouter.get('/repos/:owner/:repo/issues', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/issues`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub issues list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_ISSUES_ERROR',
        message: error.response?.data?.detail || 'Failed to list issues',
      },
    });
  }
});

/**
 * Create issue
 */
githubRouter.post('/repos/:owner/:repo/issues', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.post(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/issues`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub issue create error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_ISSUE_CREATE_ERROR',
        message: error.response?.data?.detail || 'Failed to create issue',
      },
    });
  }
});

/**
 * List pull requests
 */
githubRouter.get('/repos/:owner/:repo/pulls', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/pulls`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub PRs list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_PRS_ERROR',
        message: error.response?.data?.detail || 'Failed to list pull requests',
      },
    });
  }
});

/**
 * Create pull request
 */
githubRouter.post('/repos/:owner/:repo/pulls', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.post(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/pulls`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub PR create error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_PR_CREATE_ERROR',
        message: error.response?.data?.detail || 'Failed to create pull request',
      },
    });
  }
});

/**
 * Get file content
 */
githubRouter.get('/repos/:owner/:repo/contents/*', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const path = req.params[0] || '';
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/contents/${path}`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub contents get error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_CONTENTS_ERROR',
        message: error.response?.data?.detail || 'Failed to get contents',
      },
    });
  }
});

/**
 * Create or update file
 */
githubRouter.put('/repos/:owner/:repo/contents/*', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const path = req.params[0] || '';
    const response = await axios.put(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/contents/${path}`,
      req.body,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub file update error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_FILE_UPDATE_ERROR',
        message: error.response?.data?.detail || 'Failed to update file',
      },
    });
  }
});

/**
 * List commits
 */
githubRouter.get('/repos/:owner/:repo/commits', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/commits`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub commits list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_COMMITS_ERROR',
        message: error.response?.data?.detail || 'Failed to list commits',
      },
    });
  }
});

/**
 * List branches
 */
githubRouter.get('/repos/:owner/:repo/branches', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { owner, repo } = req.params;
    const response = await axios.get(
      `${GITHUB_SERVICE_URL}/repos/${owner}/${repo}/branches`,
      {
        headers: {
          'Authorization': req.headers.authorization || '',
        },
        params: req.query,
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub branches list error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_BRANCHES_ERROR',
        message: error.response?.data?.detail || 'Failed to list branches',
      },
    });
  }
});

/**
 * GitHub webhook receiver
 */
githubRouter.post('/webhook', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const response = await axios.post(
      `${GITHUB_SERVICE_URL}/webhook`,
      req.body,
      {
        headers: {
          'X-GitHub-Event': req.headers['x-github-event'] || '',
          'X-Hub-Signature-256': req.headers['x-hub-signature-256'] || '',
          'X-GitHub-Delivery': req.headers['x-github-delivery'] || '',
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    res.json({
      success: true,
      data: response.data,
    });
  } catch (error: any) {
    logger.error('GitHub webhook error:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: {
        code: 'GITHUB_WEBHOOK_ERROR',
        message: error.response?.data?.detail || 'Failed to process webhook',
      },
    });
  }
});
