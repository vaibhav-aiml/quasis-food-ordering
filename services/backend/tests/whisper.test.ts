import express from 'express';
import http from 'http';
import { describe, expect, it } from 'vitest';
import { PipelineOrchestrator } from '../src/agent/pipelineOrchestrator.js';
import { WhisperTranscriber } from '../src/agent/whisperTranscriber.js';
import { createRouter } from '../src/api/routes.js';
import { SwiggySearchService } from '../src/tools/swiggy/searchService.js';

describe('WhisperTranscriber & Voice API', () => {
  it('should reject empty or invalid base64 payloads gracefully', async () => {
    const result = await WhisperTranscriber.transcribe({
      audioBase64: '',
    });
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should return informative error if GROQ_API_KEY is unset', async () => {
    const originalKey = process.env.GROQ_API_KEY;
    delete process.env.GROQ_API_KEY;

    const result = await WhisperTranscriber.transcribe({
      audioBase64: 'UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=',
      mimeType: 'audio/wav',
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain('GROQ_API_KEY');

    process.env.GROQ_API_KEY = originalKey;
  });

  it('should reject requests with missing audioBase64 with HTTP 400 on live ephemeral server', async () => {
    const searchService = new SwiggySearchService();
    const orchestrator = new PipelineOrchestrator(searchService);

    const app = express();
    app.use(express.json({ limit: '25mb' }));
    app.use(createRouter(orchestrator, searchService));

    const server = http.createServer(app);
    await new Promise<void>((resolve) => server.listen(0, resolve));
    const port = (server.address() as any).port;

    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/voice/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      expect(res.status).toBe(400);
      const data = (await res.json()) as any;
      expect(data.success).toBe(false);
      expect(data.error).toContain('audioBase64');
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  });

  it('should reject non-string audioBase64 payload with HTTP 400', async () => {
    const searchService = new SwiggySearchService();
    const orchestrator = new PipelineOrchestrator(searchService);

    const app = express();
    app.use(express.json({ limit: '25mb' }));
    app.use(createRouter(orchestrator, searchService));

    const server = http.createServer(app);
    await new Promise<void>((resolve) => server.listen(0, resolve));
    const port = (server.address() as any).port;

    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/voice/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audioBase64: 12345 }),
      });

      expect(res.status).toBe(400);
      const data = (await res.json()) as any;
      expect(data.success).toBe(false);
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  });
});
