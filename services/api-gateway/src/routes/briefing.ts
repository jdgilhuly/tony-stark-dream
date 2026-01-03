import { Router, Response } from 'express';
import { AuthenticatedRequest } from '../middleware/auth.js';
import { logger } from '../utils/logger.js';

export const briefingRouter = Router();

// Mock briefing data (replace with actual service calls)
const generateMockBriefing = (userId: string) => ({
  id: `briefing-${Date.now()}`,
  userId,
  generatedAt: new Date(),
  summary: "Good morning, sir. Here's your daily briefing.",
  weather: {
    location: 'Malibu, California',
    current: {
      temperature: 72,
      condition: 'Sunny',
      humidity: 45,
      windSpeed: 8,
    },
    forecast: [
      { date: new Date(), high: 78, low: 62, condition: 'Sunny', precipitationChance: 0 },
      { date: new Date(Date.now() + 86400000), high: 75, low: 60, condition: 'Partly Cloudy', precipitationChance: 10 },
      { date: new Date(Date.now() + 172800000), high: 73, low: 58, condition: 'Cloudy', precipitationChance: 30 },
    ],
  },
  news: [
    {
      id: 'news-1',
      title: 'Tech Innovation Update',
      summary: 'Major advancements in AI technology announced today.',
      source: 'Tech News Daily',
      url: 'https://example.com/news/1',
      category: 'technology',
      publishedAt: new Date(),
    },
    {
      id: 'news-2',
      title: 'Market Analysis',
      summary: 'Stock markets show positive trends this quarter.',
      source: 'Financial Times',
      url: 'https://example.com/news/2',
      category: 'business',
      publishedAt: new Date(),
    },
  ],
  calendar: [
    {
      id: 'event-1',
      title: 'Team Meeting',
      description: 'Weekly sync with the engineering team',
      startTime: new Date(Date.now() + 3600000),
      endTime: new Date(Date.now() + 5400000),
      location: 'Conference Room A',
      isAllDay: false,
      attendees: ['Tony', 'Pepper', 'Happy'],
    },
    {
      id: 'event-2',
      title: 'Project Review',
      description: 'Quarterly project status review',
      startTime: new Date(Date.now() + 10800000),
      endTime: new Date(Date.now() + 14400000),
      isAllDay: false,
    },
  ],
  tasks: [
    {
      id: 'task-1',
      title: 'Review prototype designs',
      description: 'Review and approve the new Mark suit designs',
      dueDate: new Date(Date.now() + 86400000),
      priority: 'high' as const,
      status: 'pending' as const,
    },
    {
      id: 'task-2',
      title: 'Prepare presentation',
      description: 'Prepare slides for the board meeting',
      dueDate: new Date(Date.now() + 172800000),
      priority: 'medium' as const,
      status: 'in_progress' as const,
    },
  ],
});

briefingRouter.get('/daily', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const userId = req.user!.userId;

    // In production, this would call the briefing service
    const briefing = generateMockBriefing(userId);

    logger.info(`Daily briefing generated for user ${userId}`);

    res.json({
      success: true,
      data: briefing,
    });
  } catch (error) {
    logger.error('Briefing error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'BRIEFING_ERROR', message: 'Failed to generate briefing' },
    });
  }
});

briefingRouter.get('/weather', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const briefing = generateMockBriefing(req.user!.userId);

    res.json({
      success: true,
      data: briefing.weather,
    });
  } catch (error) {
    logger.error('Weather error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'WEATHER_ERROR', message: 'Failed to fetch weather' },
    });
  }
});

briefingRouter.get('/news', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { category, limit = '10' } = req.query;
    const briefing = generateMockBriefing(req.user!.userId);

    let news = briefing.news;
    if (category) {
      news = news.filter((n) => n.category === category);
    }
    news = news.slice(0, parseInt(limit as string, 10));

    res.json({
      success: true,
      data: news,
    });
  } catch (error) {
    logger.error('News error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'NEWS_ERROR', message: 'Failed to fetch news' },
    });
  }
});

briefingRouter.get('/calendar', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { date } = req.query;
    const briefing = generateMockBriefing(req.user!.userId);

    res.json({
      success: true,
      data: briefing.calendar,
    });
  } catch (error) {
    logger.error('Calendar error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'CALENDAR_ERROR', message: 'Failed to fetch calendar' },
    });
  }
});

briefingRouter.get('/tasks', async (req: AuthenticatedRequest, res: Response) => {
  try {
    const { status, priority } = req.query;
    const briefing = generateMockBriefing(req.user!.userId);

    let tasks = briefing.tasks;
    if (status) {
      tasks = tasks.filter((t) => t.status === status);
    }
    if (priority) {
      tasks = tasks.filter((t) => t.priority === priority);
    }

    res.json({
      success: true,
      data: tasks,
    });
  } catch (error) {
    logger.error('Tasks error:', error);
    res.status(500).json({
      success: false,
      error: { code: 'TASKS_ERROR', message: 'Failed to fetch tasks' },
    });
  }
});
