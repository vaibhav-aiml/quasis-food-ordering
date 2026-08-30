import { Request, Response, Router } from 'express';
import { PipelineOrchestrator } from '../agent/pipelineOrchestrator.js';
import { WhisperTranscriber } from '../agent/whisperTranscriber.js';
import { SwiggySearchService } from '../tools/swiggy/searchService.js';
import { PipelineEvent } from '../tools/swiggy/types.js';

// In-memory sliding window rate limiter for audio transcription (per IP) with automatic stale key eviction
const transcriptionRateLimitMap = new Map<string, number[]>();
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute
const MAX_TRANSCRIPTION_REQUESTS_PER_MIN = 20; // Max 20 requests per minute per IP

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const timestamps = transcriptionRateLimitMap.get(ip) || [];
  const validTimestamps = timestamps.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);

  if (validTimestamps.length >= MAX_TRANSCRIPTION_REQUESTS_PER_MIN) {
    transcriptionRateLimitMap.set(ip, validTimestamps);
    return true;
  }

  validTimestamps.push(now);
  transcriptionRateLimitMap.set(ip, validTimestamps);
  return false;
}

// Periodic cleanup every 5 minutes to prune any expired IP entries from memory
setInterval(() => {
  const now = Date.now();
  for (const [ip, timestamps] of transcriptionRateLimitMap.entries()) {
    const valid = timestamps.filter((t) => now - t < RATE_LIMIT_WINDOW_MS);
    if (valid.length === 0) {
      transcriptionRateLimitMap.delete(ip);
    } else {
      transcriptionRateLimitMap.set(ip, valid);
    }
  }
}, 5 * 60 * 1000).unref?.();

export function createRouter(
  orchestrator: PipelineOrchestrator,
  searchService: SwiggySearchService
): Router {
  const router = Router();

  // Health check
  router.get('/health', (_req: Request, res: Response) => {
    res.json({
      status: 'ok',
      service: 'quasis-swiggy-pipeline-backend',
      timestamp: Date.now(),
    });
  });

  // Voice transcription endpoint using Groq Whisper Large v3
  router.post('/api/voice/transcribe', async (req: Request, res: Response) => {
    try {
      const clientIp = req.ip || req.socket.remoteAddress || 'unknown';
      if (isRateLimited(clientIp)) {
        res.status(429).json({
          success: false,
          error: 'Too many transcription requests. Rate limit is 20 requests per minute.',
        });
        return;
      }

      const { audioBase64, mimeType, filename, prompt, language } = req.body;

      if (!audioBase64 || typeof audioBase64 !== 'string') {
        res.status(400).json({
          success: false,
          error: 'Field "audioBase64" is required and must be a base64 encoded audio string.',
        });
        return;
      }

      const result = await WhisperTranscriber.transcribe({
        audioBase64,
        mimeType,
        filename,
        prompt,
        language,
      });

      if (!result.success) {
        res.status(500).json(result);
        return;
      }

      res.status(200).json(result);
    } catch (err: any) {
      res.status(500).json({
        success: false,
        error: err.message || 'Internal error during audio transcription',
      });
    }
  });

  // Fetch catalog restaurants
  router.get('/api/order/restaurants', (_req: Request, res: Response) => {
    res.json({
      restaurants: searchService.getRestaurants(),
    });
  });

  // Stage 1: Post intent / prompt to start pipeline
  router.post('/api/order/intent', (req: Request, res: Response) => {
    try {
      const { prompt, city, sessionId } = req.body;

      if (!prompt || typeof prompt !== 'string') {
        res.status(400).json({ error: 'Field "prompt" is required and must be a string' });
        return;
      }

      if (!city || typeof city !== 'string' || !city.trim()) {
        res.status(400).json({ error: 'Field "city" is required and must be a non-empty string' });
        return;
      }

      const activeSessionId = orchestrator.createSession(prompt, city.trim(), sessionId);
      const state = orchestrator.getSessionState(activeSessionId);

      res.status(200).json({
        success: true,
        sessionId: activeSessionId,
        status: 'started',
        initialStage: state?.stage || 'PARSING_INTENT',
        message: `Pipeline session ${activeSessionId} initialized.`,
      });
    } catch (err: any) {
      res.status(500).json({ error: err.message || 'Failed to start pipeline' });
    }
  });

  // Stage 2 & 3: Server-Sent Events (SSE) endpoint to stream live execution trace
  router.get('/api/order/pipeline/:sessionId', (req: Request, res: Response) => {
    const { sessionId } = req.params;

    // Verify session exists
    const session = orchestrator.getSessionState(sessionId);
    if (!session) {
      res.status(404).json({ error: `Pipeline session "${sessionId}" not found` });
      return;
    }

    // Set headers for Server-Sent Events
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
    res.flushHeaders?.();

    // Replay existing events for newly connected client
    const pastEvents = orchestrator.getSessionEvents(sessionId);
    for (const ev of pastEvents) {
      res.write(`data: ${JSON.stringify(ev)}\n\n`);
    }

    // Subscribe to new real-time events
    const unsubscribe = orchestrator.subscribe(sessionId, (event: PipelineEvent) => {
      res.write(`data: ${JSON.stringify(event)}\n\n`);
      if (event.stage === 'COMPLETED' || event.stage === 'FAILED') {
        // Keep stream open briefly then client or server can close
      }
    });

    // Send heartbeat keepalive every 15 seconds
    const keepAlive = setInterval(() => {
      res.write(': keep-alive\n\n');
    }, 15000);

    // Clean up on disconnect
    req.on('close', () => {
      clearInterval(keepAlive);
      unsubscribe();
      res.end();
    });
  });

  // Stage 4 & 5: Approval & Deep Link generation
  router.post('/api/order/approve', async (req: Request, res: Response) => {
    try {
      const { sessionId, approved = true, selectedItemId } = req.body;

      if (!sessionId) {
        res.status(400).json({ error: 'Field "sessionId" is required' });
        return;
      }

      const result = await orchestrator.approveOrder(sessionId, approved, selectedItemId);
      res.status(200).json(result);
    } catch (err: any) {
      res.status(400).json({ error: err.message || 'Failed to approve order' });
    }
  });

  // State snapshot endpoint
  router.get('/api/order/state/:sessionId', (req: Request, res: Response) => {
    const { sessionId } = req.params;
    const state = orchestrator.getSessionState(sessionId);
    if (!state) {
      res.status(404).json({ error: `Session "${sessionId}" not found` });
      return;
    }
    res.json({
      state,
      events: orchestrator.getSessionEvents(sessionId),
    });
  });

  return router;
}
