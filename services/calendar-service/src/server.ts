import express, { Request, Response, NextFunction } from 'express';
import { google, calendar_v3 } from 'googleapis';
import jwt from 'jsonwebtoken';
import { v4 as uuidv4 } from 'uuid';
import Redis from 'ioredis';
import winston from 'winston';

// Configuration
const PORT = process.env.PORT ?? 8006;
const JWT_SECRET = process.env.JWT_SECRET ?? 'development-secret-change-in-production';
const REDIS_URL = process.env.REDIS_URL ?? 'redis://localhost:6379/0';
const GOOGLE_CLIENT_ID = process.env.GOOGLE_CLIENT_ID ?? '';
const GOOGLE_CLIENT_SECRET = process.env.GOOGLE_CLIENT_SECRET ?? '';
const GOOGLE_REDIRECT_URI = process.env.GOOGLE_REDIRECT_URI ?? 'http://localhost:8006/auth/callback';
const CACHE_TTL = 900; // 15 minutes

// Logger
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [new winston.transports.Console()],
});

// Redis client
const redis = new Redis(REDIS_URL);

// OAuth2 client
const oauth2Client = new google.auth.OAuth2(
  GOOGLE_CLIENT_ID,
  GOOGLE_CLIENT_SECRET,
  GOOGLE_REDIRECT_URI
);

// Express app
const app = express();
app.use(express.json());

// Types
interface AuthenticatedRequest extends Request {
  user?: { userId: string };
}

interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  startTime: string;
  endTime: string;
  location?: string;
  isAllDay: boolean;
  attendees: string[];
  status: string;
  htmlLink?: string;
}

interface TokenData {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

// Middleware: JWT Authentication
const authenticate = (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    res.status(401).json({ error: 'Missing authorization token' });
    return;
  }

  try {
    const token = authHeader.slice(7);
    const decoded = jwt.verify(token, JWT_SECRET) as { userId: string };
    req.user = decoded;
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
};

// Helper: Get user's OAuth tokens from Redis
async function getUserTokens(userId: string): Promise<TokenData | null> {
  const data = await redis.get(`calendar:tokens:${userId}`);
  return data ? JSON.parse(data) : null;
}

// Helper: Save user's OAuth tokens to Redis
async function saveUserTokens(userId: string, tokens: TokenData): Promise<void> {
  await redis.set(`calendar:tokens:${userId}`, JSON.stringify(tokens));
}

// Helper: Get authenticated calendar client
async function getCalendarClient(userId: string): Promise<calendar_v3.Calendar | null> {
  const tokens = await getUserTokens(userId);
  if (!tokens) return null;

  oauth2Client.setCredentials({
    access_token: tokens.accessToken,
    refresh_token: tokens.refreshToken,
  });

  // Refresh token if expired
  if (Date.now() >= tokens.expiresAt) {
    try {
      const { credentials } = await oauth2Client.refreshAccessToken();
      await saveUserTokens(userId, {
        accessToken: credentials.access_token!,
        refreshToken: credentials.refresh_token ?? tokens.refreshToken,
        expiresAt: credentials.expiry_date ?? Date.now() + 3600000,
      });
      oauth2Client.setCredentials(credentials);
    } catch (error) {
      logger.error('Token refresh failed:', error);
      return null;
    }
  }

  return google.calendar({ version: 'v3', auth: oauth2Client });
}

// Helper: Parse Google Calendar event
function parseEvent(event: calendar_v3.Schema$Event): CalendarEvent {
  const start = event.start?.dateTime ?? event.start?.date ?? '';
  const end = event.end?.dateTime ?? event.end?.date ?? '';
  const isAllDay = !event.start?.dateTime;

  return {
    id: event.id ?? uuidv4(),
    title: event.summary ?? 'Untitled Event',
    description: event.description ?? undefined,
    startTime: start,
    endTime: end,
    location: event.location ?? undefined,
    isAllDay,
    attendees: event.attendees?.map(a => a.email ?? '').filter(Boolean) ?? [],
    status: event.status ?? 'confirmed',
    htmlLink: event.htmlLink ?? undefined,
  };
}

// Routes

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'calendar-service',
    timestamp: new Date().toISOString(),
  });
});

// OAuth: Get authorization URL
app.get('/auth/url', authenticate, (req: AuthenticatedRequest, res) => {
  const scopes = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events.readonly',
  ];

  const state = Buffer.from(JSON.stringify({ userId: req.user!.userId })).toString('base64');

  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: scopes,
    state,
    prompt: 'consent',
  });

  res.json({ authUrl });
});

// OAuth: Handle callback
app.get('/auth/callback', async (req, res) => {
  const { code, state } = req.query;

  if (!code || !state) {
    res.status(400).send('Missing code or state');
    return;
  }

  try {
    const { userId } = JSON.parse(Buffer.from(state as string, 'base64').toString());
    const { tokens } = await oauth2Client.getToken(code as string);

    await saveUserTokens(userId, {
      accessToken: tokens.access_token!,
      refreshToken: tokens.refresh_token!,
      expiresAt: tokens.expiry_date ?? Date.now() + 3600000,
    });

    logger.info(`Calendar connected for user ${userId}`);
    res.send('Calendar connected successfully! You can close this window.');
  } catch (error) {
    logger.error('OAuth callback error:', error);
    res.status(500).send('Failed to connect calendar');
  }
});

// Check connection status
app.get('/auth/status', authenticate, async (req: AuthenticatedRequest, res) => {
  const tokens = await getUserTokens(req.user!.userId);
  res.json({ connected: !!tokens });
});

// Disconnect calendar
app.post('/auth/disconnect', authenticate, async (req: AuthenticatedRequest, res) => {
  await redis.del(`calendar:tokens:${req.user!.userId}`);
  res.json({ success: true });
});

// Get events
app.get('/events', authenticate, async (req: AuthenticatedRequest, res) => {
  const userId = req.user!.userId;
  const { startDate, endDate, maxResults = '50' } = req.query;

  // Check cache first
  const cacheKey = `calendar:events:${userId}:${startDate}:${endDate}`;
  const cached = await redis.get(cacheKey);
  if (cached) {
    res.json({ events: JSON.parse(cached), cached: true });
    return;
  }

  const calendar = await getCalendarClient(userId);
  if (!calendar) {
    res.status(401).json({ error: 'Calendar not connected' });
    return;
  }

  try {
    const timeMin = startDate ? new Date(startDate as string).toISOString() : new Date().toISOString();
    const timeMax = endDate
      ? new Date(endDate as string).toISOString()
      : new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString();

    const response = await calendar.events.list({
      calendarId: 'primary',
      timeMin,
      timeMax,
      maxResults: parseInt(maxResults as string, 10),
      singleEvents: true,
      orderBy: 'startTime',
    });

    const events = (response.data.items ?? []).map(parseEvent);

    // Cache the results
    await redis.set(cacheKey, JSON.stringify(events), 'EX', CACHE_TTL);

    res.json({ events, cached: false });
  } catch (error) {
    logger.error('Failed to fetch events:', error);
    res.status(500).json({ error: 'Failed to fetch events' });
  }
});

// Get today's events
app.get('/events/today', authenticate, async (req: AuthenticatedRequest, res) => {
  const userId = req.user!.userId;

  const cacheKey = `calendar:today:${userId}:${new Date().toDateString()}`;
  const cached = await redis.get(cacheKey);
  if (cached) {
    res.json({ events: JSON.parse(cached), cached: true });
    return;
  }

  const calendar = await getCalendarClient(userId);
  if (!calendar) {
    res.status(401).json({ error: 'Calendar not connected' });
    return;
  }

  try {
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const endOfDay = new Date(startOfDay.getTime() + 24 * 60 * 60 * 1000);

    const response = await calendar.events.list({
      calendarId: 'primary',
      timeMin: startOfDay.toISOString(),
      timeMax: endOfDay.toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
    });

    const events = (response.data.items ?? []).map(parseEvent);

    await redis.set(cacheKey, JSON.stringify(events), 'EX', CACHE_TTL);

    res.json({ events, cached: false });
  } catch (error) {
    logger.error('Failed to fetch today events:', error);
    res.status(500).json({ error: 'Failed to fetch events' });
  }
});

// Get upcoming events
app.get('/events/upcoming', authenticate, async (req: AuthenticatedRequest, res) => {
  const userId = req.user!.userId;
  const { hours = '24' } = req.query;

  const calendar = await getCalendarClient(userId);
  if (!calendar) {
    res.status(401).json({ error: 'Calendar not connected' });
    return;
  }

  try {
    const now = new Date();
    const endTime = new Date(now.getTime() + parseInt(hours as string, 10) * 60 * 60 * 1000);

    const response = await calendar.events.list({
      calendarId: 'primary',
      timeMin: now.toISOString(),
      timeMax: endTime.toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
      maxResults: 10,
    });

    const events = (response.data.items ?? []).map(parseEvent);

    res.json({ events });
  } catch (error) {
    logger.error('Failed to fetch upcoming events:', error);
    res.status(500).json({ error: 'Failed to fetch events' });
  }
});

// Get event by ID
app.get('/events/:eventId', authenticate, async (req: AuthenticatedRequest, res) => {
  const userId = req.user!.userId;
  const { eventId } = req.params;

  const calendar = await getCalendarClient(userId);
  if (!calendar) {
    res.status(401).json({ error: 'Calendar not connected' });
    return;
  }

  try {
    const response = await calendar.events.get({
      calendarId: 'primary',
      eventId,
    });

    res.json({ event: parseEvent(response.data) });
  } catch (error) {
    logger.error('Failed to fetch event:', error);
    res.status(404).json({ error: 'Event not found' });
  }
});

// List calendars
app.get('/calendars', authenticate, async (req: AuthenticatedRequest, res) => {
  const calendar = await getCalendarClient(req.user!.userId);
  if (!calendar) {
    res.status(401).json({ error: 'Calendar not connected' });
    return;
  }

  try {
    const response = await calendar.calendarList.list();

    const calendars = (response.data.items ?? []).map(cal => ({
      id: cal.id,
      summary: cal.summary,
      description: cal.description,
      primary: cal.primary,
      backgroundColor: cal.backgroundColor,
    }));

    res.json({ calendars });
  } catch (error) {
    logger.error('Failed to list calendars:', error);
    res.status(500).json({ error: 'Failed to list calendars' });
  }
});

// Start server
app.listen(PORT, () => {
  logger.info(`Calendar service listening on port ${PORT}`);
});

export { app };
