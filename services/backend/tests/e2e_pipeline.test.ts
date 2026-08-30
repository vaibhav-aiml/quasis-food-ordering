import cors from 'cors';
import express from 'express';
import http from 'http';
import { describe, expect, it } from 'vitest';
import { PipelineOrchestrator } from '../src/agent/pipelineOrchestrator.js';
import { createRouter } from '../src/api/routes.js';
import { SwiggySearchService } from '../src/tools/swiggy/searchService.js';

describe('End-to-End Live Food Ordering Pipeline API Test', () => {
  it('rejects intent submission with 400 if city is missing from request body', async () => {
    const searchService = new SwiggySearchService();
    const orchestrator = new PipelineOrchestrator(searchService);

    const app = express();
    app.use(cors());
    app.use(express.json());
    app.use(createRouter(orchestrator, searchService));

    const server = http.createServer(app);
    await new Promise<void>((resolve) => server.listen(0, resolve));
    const port = (server.address() as any).port;

    try {
      const intentRes = await fetch(`http://localhost:${port}/api/order/intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'Find the best-rated iced latte under 200' }),
      });

      expect(intentRes.status).toBe(400);
      const intentData = (await intentRes.json()) as any;
      expect(intentData.error).toContain('city');
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  });

  it('handles intent submission, state polling, and final order approval', async () => {
    const searchService = new SwiggySearchService();
    const orchestrator = new PipelineOrchestrator(searchService);

    const app = express();
    app.use(cors());
    app.use(express.json());
    app.use(createRouter(orchestrator, searchService));

    const server = http.createServer(app);
    await new Promise<void>((resolve) => server.listen(0, resolve));
    const port = (server.address() as any).port;

    try {
      // 1. Submit Intent with city
      const intentRes = await fetch(`http://localhost:${port}/api/order/intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: 'Find the best-rated iced latte under 200',
          city: 'Bengaluru',
        }),
      });

      expect(intentRes.status).toBe(200);
      const intentData = (await intentRes.json()) as any;
      expect(intentData.success).toBe(true);
      expect(intentData.sessionId).toBeDefined();

      const sessionId = intentData.sessionId;

      // 2. Poll for pipeline completion
      let stateData: any = null;
      for (let i = 0; i < 40; i++) {
        await new Promise((resolve) => setTimeout(resolve, 200));
        const stateRes = await fetch(`http://localhost:${port}/api/order/state/${sessionId}`);
        stateData = (await stateRes.json()) as any;
        if (stateData?.state?.stage === 'AWAITING_APPROVAL') {
          break;
        }
      }

      expect(stateData.state.stage).toBe('AWAITING_APPROVAL');
      expect(stateData.state.intent.maxBudget).toBe(200);
      expect(stateData.state.recommendedItem.price).toBeLessThanOrEqual(200);
      expect(stateData.state.deepLink).toContain('swiggy://');

      // 3. Approve Order
      const approveRes = await fetch(`http://localhost:${port}/api/order/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, approved: true }),
      });

      expect(approveRes.status).toBe(200);
      const approveData = (await approveRes.json()) as any;

      expect(approveData.success).toBe(true);
      expect(approveData.deepLink).toContain('swiggy://');
      expect(approveData.webUrl).toContain('https://www.swiggy.com/restaurants/');
      expect(approveData.item.price).toBeLessThanOrEqual(200);
    } finally {
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
  }, 15000);
});
