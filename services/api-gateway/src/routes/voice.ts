import { Router, Request, Response } from 'express';
import type { Router as RouterType } from 'express';
import axios from 'axios';
import multer from 'multer';

const router: RouterType = Router();
const VOICE_PROCESSING_URL = process.env.VOICE_PROCESSING_URL || 'http://localhost:8002';

// Configure multer for audio file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB max file size
  },
  fileFilter: (req, file, cb) => {
    // Accept audio files
    if (file.mimetype.startsWith('audio/')) {
      cb(null, true);
    } else {
      cb(new Error('Only audio files are allowed'));
    }
  },
});

// Transcribe audio to text
router.post('/transcribe', upload.single('audio'), async (req: Request, res: Response) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No audio file provided' });
    }

    const formData = new FormData();
    formData.append('audio', new Blob([req.file.buffer], { type: req.file.mimetype }), req.file.originalname);

    const response = await axios.post(`${VOICE_PROCESSING_URL}/transcribe`, formData, {
      headers: {
        'Authorization': req.headers.authorization,
        'Content-Type': 'multipart/form-data',
      },
    });

    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Transcription failed';
    res.status(status).json({ error: message });
  }
});

// Synthesize text to speech
router.post('/synthesize', async (req: Request, res: Response) => {
  try {
    const response = await axios.post(`${VOICE_PROCESSING_URL}/synthesize`, req.body, {
      headers: {
        'Authorization': req.headers.authorization,
        'Content-Type': 'application/json',
      },
      responseType: 'arraybuffer',
    });

    res.set('Content-Type', 'audio/mpeg');
    res.send(Buffer.from(response.data));
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Speech synthesis failed';
    res.status(status).json({ error: message });
  }
});

// Get available voices
router.get('/voices', async (req: Request, res: Response) => {
  try {
    const response = await axios.get(`${VOICE_PROCESSING_URL}/voices`, {
      headers: { 'Authorization': req.headers.authorization },
    });
    res.json(response.data);
  } catch (error: any) {
    const status = error.response?.status || 500;
    const message = error.response?.data?.detail || 'Failed to get voices';
    res.status(status).json({ error: message });
  }
});

// Stream transcription (WebSocket endpoint info)
router.get('/stream-info', (req: Request, res: Response) => {
  res.json({
    transcribe: {
      websocket: `ws://${req.headers.host}/ws/transcribe`,
      description: 'WebSocket endpoint for real-time audio transcription',
    },
    synthesize: {
      websocket: `ws://${req.headers.host}/ws/synthesize`,
      description: 'WebSocket endpoint for real-time speech synthesis',
    },
  });
});

export default router;
